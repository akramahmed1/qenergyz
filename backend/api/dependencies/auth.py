"""
Authentication Dependencies

JWT authentication, OAuth2, MFA, and role-based access control.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import jwt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordBearer
from passlib.context import CryptContext
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
import redis.asyncio as aioredis
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models.database import get_db
from ..models.user import User, UserRole, UserSession
from ..utils.config import get_settings


class TokenData:
    """Token data for validation"""
    def __init__(self, user_id: str, type: str, payload: dict = None):
        self.user_id = user_id
        self.type = type
        self.payload = payload or {}


logger = structlog.get_logger(__name__)
settings = get_settings()

# Security configurations
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
argon2_hasher = PasswordHasher()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")
security = HTTPBearer()

# Redis for session management
redis_client: Optional[aioredis.Redis] = None


class AuthenticationError(HTTPException):
    """Authentication related errors"""
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthorizationError(HTTPException):
    """Authorization related errors"""
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


async def get_redis():
    """Get Redis client for session management"""
    global redis_client
    if not redis_client:
        redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
    return redis_client


class PasswordHandler:
    """Password hashing and verification using Argon2 and bcrypt"""
    
    @staticmethod
    def hash_password(password: str, use_argon2: bool = True) -> str:
        """Hash password using Argon2 (preferred) or bcrypt"""
        if use_argon2:
            return argon2_hasher.hash(password)
        else:
            return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """Verify password against hash, try Argon2 first then bcrypt"""
        try:
            # Try Argon2 first
            argon2_hasher.verify(hashed_password, password)
            return True
        except VerifyMismatchError:
            # Fall back to bcrypt
            return pwd_context.verify(password, hashed_password)
    
    @staticmethod
    def needs_rehash(hashed_password: str) -> bool:
        """Check if password needs rehashing"""
        try:
            return argon2_hasher.check_needs_rehash(hashed_password)
        except:
            return pwd_context.identify(hashed_password) == "bcrypt"


class JWTHandler:
    """JWT token creation and validation"""
    
    @staticmethod
    def create_access_token(
        data: dict,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=settings.jwt_expiration_hours)
        
        to_encode.update({"exp": expire, "type": "access"})
        return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)
    
    @staticmethod
    def create_refresh_token(data: dict) -> str:
        """Create refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=30)  # Refresh tokens last 30 days
        to_encode.update({"exp": expire, "type": "refresh"})
        return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)
    
    @staticmethod
    def verify_token(token: str) -> TokenData:
        """Verify and decode token"""
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
            user_id: str = payload.get("sub")
            token_type: str = payload.get("type")
            
            if user_id is None:
                raise AuthenticationError("Invalid token: missing subject")
            
            return TokenData(user_id=user_id, type=token_type, payload=payload)
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.JWTError:
            raise AuthenticationError("Invalid token")


class BruteForceProtection:
    """Brute force protection using Redis"""
    
    def __init__(self, max_attempts: int = 5, lockout_time: int = 900):
        self.max_attempts = max_attempts
        self.lockout_time = lockout_time  # 15 minutes
    
    async def check_attempts(self, identifier: str) -> bool:
        """Check if identifier is locked out"""
        redis = await get_redis()
        attempts_key = f"login_attempts:{identifier}"
        lockout_key = f"lockout:{identifier}"
        
        # Check if locked out
        if await redis.exists(lockout_key):
            return False
        
        # Get current attempts
        attempts = await redis.get(attempts_key)
        if attempts and int(attempts) >= self.max_attempts:
            # Lock out the identifier
            await redis.setex(lockout_key, self.lockout_time, "locked")
            await redis.delete(attempts_key)
            return False
        
        return True
    
    async def record_failed_attempt(self, identifier: str):
        """Record a failed login attempt"""
        redis = await get_redis()
        attempts_key = f"login_attempts:{identifier}"
        
        # Increment attempts with expiry
        await redis.incr(attempts_key)
        await redis.expire(attempts_key, self.lockout_time)
    
    async def clear_attempts(self, identifier: str):
        """Clear failed attempts on successful login"""
        redis = await get_redis()
        attempts_key = f"login_attempts:{identifier}"
        lockout_key = f"lockout:{identifier}"
        
        await redis.delete(attempts_key)
        await redis.delete(lockout_key)


class SessionManager:
    """User session management"""
    
    @staticmethod
    async def create_session(
        user_id: str, 
        request: Request,
        db: AsyncSession
    ) -> str:
        """Create user session"""
        redis = await get_redis()
        session_id = f"session:{user_id}:{datetime.utcnow().timestamp()}"
        
        session_data = {
            "user_id": user_id,
            "ip_address": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown"),
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat()
        }
        
        # Store in Redis
        await redis.hset(session_id, mapping=session_data)
        await redis.expire(session_id, settings.jwt_expiration_hours * 3600)
        
        # Store in database for audit
        db_session = UserSession(
            session_id=session_id,
            user_id=user_id,
            ip_address=session_data["ip_address"],
            user_agent=session_data["user_agent"]
        )
        db.add(db_session)
        await db.commit()
        
        return session_id
    
    @staticmethod
    async def validate_session(session_id: str) -> bool:
        """Validate user session"""
        redis = await get_redis()
        return await redis.exists(session_id)
    
    @staticmethod
    async def invalidate_session(session_id: str):
        """Invalidate user session"""
        redis = await get_redis()
        await redis.delete(session_id)


# Initialize brute force protection
brute_force_protection = BruteForceProtection()


async def authenticate_user(
    email: str,
    password: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Authenticate user with brute force protection"""
    
    # Check brute force protection
    if not await brute_force_protection.check_attempts(email):
        await asyncio.sleep(2)  # Rate limit failed attempts
        raise AuthenticationError("Account temporarily locked due to multiple failed attempts")
    
    # Get user from database
    result = await db.execute(
        select(User).where(User.email == email)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        await brute_force_protection.record_failed_attempt(email)
        await asyncio.sleep(1)  # Rate limit
        raise AuthenticationError("Invalid email or password")
    
    # Check if user is active
    if not user.is_active:
        raise AuthenticationError("Account is disabled")
    
    # Verify password
    if not PasswordHandler.verify_password(password, user.password_hash):
        await brute_force_protection.record_failed_attempt(email)
        await asyncio.sleep(1)  # Rate limit
        raise AuthenticationError("Invalid email or password")
    
    # Clear failed attempts on successful login
    await brute_force_protection.clear_attempts(email)
    
    # Update last login
    user.last_login_at = datetime.utcnow()
    user.last_login_ip = request.client.host if request.client else "unknown"
    await db.commit()
    
    logger.info("User authenticated successfully", user_id=user.id, email=user.email)
    
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    
    token = credentials.credentials
    token_data = JWTHandler.verify_token(token)
    
    if token_data.type != "access":
        raise AuthenticationError("Invalid token type")
    
    # Get user from database
    result = await db.execute(
        select(User).where(User.id == token_data.user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise AuthenticationError("User not found")
    
    if not user.is_active:
        raise AuthenticationError("User account is disabled")
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise AuthenticationError("Inactive user")
    return current_user


def require_roles(required_roles: List[UserRole]):
    """Dependency to require specific roles"""
    async def check_roles(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        if current_user.role not in required_roles:
            raise AuthorizationError(
                f"Insufficient permissions. Required roles: {[role.value for role in required_roles]}"
            )
        return current_user
    
    return check_roles


def require_admin():
    """Dependency to require admin role"""
    return require_roles([UserRole.ADMIN, UserRole.SUPER_ADMIN])


def require_trader():
    """Dependency to require trader role or above"""
    return require_roles([UserRole.TRADER, UserRole.ADMIN, UserRole.SUPER_ADMIN])


async def validate_api_key(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Validate API key authentication"""
    api_key = request.headers.get("X-API-Key")
    
    if not api_key:
        return None
    
    # Get user by API key
    result = await db.execute(
        select(User).where(User.api_key == api_key, User.is_active == True)
    )
    user = result.scalar_one_or_none()
    
    if user:
        # Update API key usage
        user.api_key_last_used = datetime.utcnow()
        await db.commit()
        
        logger.info("API key authenticated", user_id=user.id, api_key=api_key[:8] + "...")
    
    return user