"""
Rate Limiting Dependencies

Advanced rate limiting with Redis backend and user-based limits.
"""

import hashlib
from typing import Callable
from fastapi import Request, HTTPException, status
from slowapi import Limiter
from slowapi.util import get_remote_address
import redis.asyncio as aioredis
import structlog

from ..utils.config import get_settings


logger = structlog.get_logger(__name__)
settings = get_settings()

# Redis client for rate limiting
redis_client: aioredis.Redis = None


async def get_redis_for_limiter():
    """Get Redis client for rate limiting"""
    global redis_client
    if not redis_client:
        redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
    return redis_client


def get_user_id_for_rate_limiting(request: Request) -> str:
    """Get user ID for rate limiting, fall back to IP address"""
    # Try to get user ID from token
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            from .auth import JWTHandler
            token = auth_header.split(" ")[1]
            token_data = JWTHandler.verify_token(token)
            return f"user:{token_data.user_id}"
        except:
            pass
    
    # Fall back to IP address
    return f"ip:{get_remote_address(request)}"


def get_api_key_for_rate_limiting(request: Request) -> str:
    """Get API key for rate limiting"""
    api_key = request.headers.get("X-API-Key", "")
    if api_key:
        # Hash the API key for privacy
        return f"api:{hashlib.sha256(api_key.encode()).hexdigest()[:16]}"
    return get_user_id_for_rate_limiting(request)


# Create limiter instance
limiter = Limiter(
    key_func=get_user_id_for_rate_limiting,
    storage_uri=settings.redis_url,
    default_limits=[f"{settings.rate_limit_per_minute}/minute"]
)


class RateLimitExceeded(HTTPException):
    """Rate limit exceeded exception"""
    def __init__(self, detail: str = "Rate limit exceeded"):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers={"Retry-After": "60"}
        )


async def check_rate_limit(
    request: Request,
    limit_per_minute: int = None,
    limit_per_hour: int = None
):
    """Custom rate limiting check"""
    if not limit_per_minute and not limit_per_hour:
        return  # No limits specified
    
    redis = await get_redis_for_limiter()
    identifier = get_user_id_for_rate_limiting(request)
    
    # Check per-minute limit
    if limit_per_minute:
        minute_key = f"rate_limit:minute:{identifier}"
        current_minute = await redis.incr(minute_key)
        if current_minute == 1:
            await redis.expire(minute_key, 60)
        
        if current_minute > limit_per_minute:
            logger.warning(
                "Rate limit exceeded (per minute)",
                identifier=identifier,
                limit=limit_per_minute,
                current=current_minute
            )
            raise RateLimitExceeded("Rate limit exceeded: too many requests per minute")
    
    # Check per-hour limit
    if limit_per_hour:
        hour_key = f"rate_limit:hour:{identifier}"
        current_hour = await redis.incr(hour_key)
        if current_hour == 1:
            await redis.expire(hour_key, 3600)
        
        if current_hour > limit_per_hour:
            logger.warning(
                "Rate limit exceeded (per hour)",
                identifier=identifier,
                limit=limit_per_hour,
                current=current_hour
            )
            raise RateLimitExceeded("Rate limit exceeded: too many requests per hour")


def rate_limit(per_minute: int = None, per_hour: int = None):
    """Rate limiting decorator dependency"""
    async def check_limits(request: Request):
        await check_rate_limit(request, per_minute, per_hour)
    
    return check_limits


# Common rate limit dependencies
async def auth_rate_limit(request: Request):
    """Rate limit for authentication endpoints"""
    await check_rate_limit(request, limit_per_minute=10, limit_per_hour=100)


async def api_rate_limit(request: Request):
    """Standard API rate limit"""
    await check_rate_limit(request, limit_per_minute=60, limit_per_hour=1000)


async def trading_rate_limit(request: Request):
    """Rate limit for trading endpoints"""
    await check_rate_limit(request, limit_per_minute=30, limit_per_hour=500)


async def admin_rate_limit(request: Request):
    """Rate limit for admin endpoints"""
    await check_rate_limit(request, limit_per_minute=100, limit_per_hour=2000)