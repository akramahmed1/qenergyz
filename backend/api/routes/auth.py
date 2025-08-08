"""
Authentication Routes

JWT authentication, OAuth2, MFA, and session management endpoints.
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from ..dependencies.auth import (
    authenticate_user,
    JWTHandler,
    PasswordHandler,
    get_current_user,
    get_current_active_user,
    SessionManager
)
from ..dependencies.database import get_db
from ..dependencies.rate_limiting import auth_rate_limit
from ..dependencies.logging import audit_logger
from ..models.user import User, UserRole
from ..models.audit_log import AuditAction, AuditResource

logger = structlog.get_logger(__name__)
router = APIRouter()


# Request/Response Models
class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    company: Optional[str] = Field(None, max_length=200)
    job_title: Optional[str] = Field(None, max_length=100)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class PasswordChange(BaseModel):
    current_password: str = Field(..., min_length=8, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(auth_rate_limit)
):
    """Authenticate user and return JWT tokens"""
    
    # Authenticate user
    user = await authenticate_user(
        email=form_data.username,  # OAuth2PasswordRequestForm uses 'username' field
        password=form_data.password,
        request=request,
        db=db
    )
    
    # Create JWT tokens
    access_token = JWTHandler.create_access_token(
        data={"sub": user.id, "email": user.email, "role": user.role.value}
    )
    refresh_token = JWTHandler.create_refresh_token(
        data={"sub": user.id}
    )
    
    # Create session
    session_id = await SessionManager.create_session(user.id, request, db)
    
    # Log successful login
    await audit_logger.log_user_action(
        user_id=user.id,
        action=AuditAction.LOGIN,
        resource=AuditResource.USER,
        resource_id=user.id,
        request=request
    )
    
    logger.info("User logged in successfully", user_id=user.id, email=user.email)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=3600 * 24,  # 24 hours
        user={
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role.value,
            "is_verified": user.is_verified
        }
    )


@router.post("/register", response_model=dict)
async def register(
    user_data: UserRegister,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(auth_rate_limit)
):
    """Register new user account"""
    
    # Check if user already exists
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Validate password strength
    password_validation = PasswordHandler.validate_password_strength(user_data.password)
    if not password_validation["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password requirements not met: {', '.join(password_validation['errors'])}"
        )
    
    # Create new user
    new_user = User(
        email=user_data.email,
        password_hash=PasswordHandler.hash_password(user_data.password),
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        phone=user_data.phone,
        company=user_data.company,
        job_title=user_data.job_title,
        role=UserRole.USER,
        is_active=True,
        is_verified=False  # Email verification required
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # Log user creation
    await audit_logger.log_user_action(
        user_id=new_user.id,
        action=AuditAction.USER_CREATED,
        resource=AuditResource.USER,
        resource_id=new_user.id,
        details={"email": new_user.email, "role": new_user.role.value},
        request=request
    )
    
    logger.info("New user registered", user_id=new_user.id, email=new_user.email)
    
    return {
        "message": "User registered successfully",
        "user_id": new_user.id,
        "email": new_user.email,
        "verification_required": True
    }


@router.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Logout current user and invalidate session"""
    
    # Invalidate session if available
    # This would require session tracking in the token or headers
    
    # Log logout
    await audit_logger.log_user_action(
        user_id=current_user.id,
        action=AuditAction.LOGOUT,
        resource=AuditResource.USER,
        resource_id=current_user.id,
        request=request
    )
    
    logger.info("User logged out", user_id=current_user.id)
    
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=dict)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user information"""
    
    return {
        "id": current_user.id,
        "email": current_user.email,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "role": current_user.role.value,
        "is_verified": current_user.is_verified,
        "is_active": current_user.is_active,
        "last_login_at": current_user.last_login_at,
        "company": current_user.company,
        "job_title": current_user.job_title,
        "region": current_user.region,
        "kyc_status": current_user.kyc_status,
        "created_at": current_user.created_at
    }


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Change user password"""
    
    # Verify current password
    if not PasswordHandler.verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Validate new password strength
    password_validation = PasswordHandler.validate_password_strength(password_data.new_password)
    if not password_validation["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password requirements not met: {', '.join(password_validation['errors'])}"
        )
    
    # Update password
    current_user.password_hash = PasswordHandler.hash_password(password_data.new_password)
    current_user.password_changed_at = datetime.utcnow()
    
    await db.commit()
    
    # Log password change
    await audit_logger.log_user_action(
        user_id=current_user.id,
        action=AuditAction.PASSWORD_CHANGE,
        resource=AuditResource.USER,
        resource_id=current_user.id,
        request=request
    )
    
    logger.info("Password changed", user_id=current_user.id)
    
    return {"message": "Password changed successfully"}