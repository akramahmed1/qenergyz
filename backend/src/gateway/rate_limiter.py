"""
Rate Limiter for API Gateway

Implements various rate limiting strategies:
- Fixed window
- Sliding window  
- Token bucket
- Leaky bucket
"""

import asyncio
import time
from typing import Dict, Optional, Union
from datetime import datetime, timedelta
from enum import Enum
import structlog
import redis.asyncio as aioredis
from pydantic import BaseModel, Field

from ..config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class RateLimitStrategy(str, Enum):
    """Rate limiting strategies"""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"


class RateLimitConfig(BaseModel):
    """Rate limit configuration"""
    strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW
    requests_per_minute: int = Field(default=100, ge=1)
    requests_per_hour: int = Field(default=1000, ge=1)
    requests_per_day: int = Field(default=10000, ge=1)
    burst_limit: int = Field(default=20, ge=1)
    
    # Token bucket specific
    bucket_capacity: int = Field(default=100, ge=1)
    refill_rate: float = Field(default=1.0, ge=0.1)  # tokens per second
    
    # Leaky bucket specific
    leak_rate: float = Field(default=0.5, ge=0.1)  # requests per second


class RateLimitResult(BaseModel):
    """Result of rate limit check"""
    allowed: bool
    requests_remaining: int
    reset_time: datetime
    retry_after: Optional[int] = None  # seconds


class RateLimiter:
    """
    Advanced rate limiter with multiple strategies
    
    Supports different rate limiting algorithms and provides
    fine-grained control over API access patterns.
    """
    
    def __init__(self, redis_client: Optional[aioredis.Redis] = None):
        self.redis_client = redis_client
        self._local_cache: Dict[str, Dict] = {}  # Fallback for Redis unavailability
        
        # Default configurations per user tier
        self.default_configs = {
            "free": RateLimitConfig(
                requests_per_minute=10,
                requests_per_hour=100,
                requests_per_day=1000,
                burst_limit=5
            ),
            "basic": RateLimitConfig(
                requests_per_minute=50,
                requests_per_hour=500,
                requests_per_day=5000,
                burst_limit=10
            ),
            "premium": RateLimitConfig(
                requests_per_minute=200,
                requests_per_hour=2000,
                requests_per_day=20000,
                burst_limit=50
            ),
            "enterprise": RateLimitConfig(
                requests_per_minute=1000,
                requests_per_hour=10000,
                requests_per_day=100000,
                burst_limit=100
            )
        }
    
    async def initialize(self, redis_client: aioredis.Redis):
        """Initialize rate limiter with Redis client"""
        self.redis_client = redis_client
        try:
            await self.redis_client.ping()
            logger.info("Rate limiter initialized with Redis")
        except Exception as e:
            logger.warning("Rate limiter falling back to local cache", error=str(e))
    
    async def check_rate_limit(
        self, 
        identifier: str, 
        config: Optional[RateLimitConfig] = None,
        user_tier: str = "basic"
    ) -> RateLimitResult:
        """
        Check if request is within rate limits
        
        Args:
            identifier: Unique identifier (user_id, IP, etc.)
            config: Custom rate limit configuration
            user_tier: User tier for default configuration
            
        Returns:
            Rate limit check result
        """
        if config is None:
            config = self.default_configs.get(user_tier, self.default_configs["basic"])
        
        if config.strategy == RateLimitStrategy.FIXED_WINDOW:
            return await self._fixed_window_check(identifier, config)
        elif config.strategy == RateLimitStrategy.SLIDING_WINDOW:
            return await self._sliding_window_check(identifier, config)
        elif config.strategy == RateLimitStrategy.TOKEN_BUCKET:
            return await self._token_bucket_check(identifier, config)
        elif config.strategy == RateLimitStrategy.LEAKY_BUCKET:
            return await self._leaky_bucket_check(identifier, config)
        else:
            raise ValueError(f"Unknown rate limit strategy: {config.strategy}")
    
    async def _fixed_window_check(
        self, 
        identifier: str, 
        config: RateLimitConfig
    ) -> RateLimitResult:
        """Fixed window rate limiting"""
        now = datetime.utcnow()
        window_start = now.replace(second=0, microsecond=0)
        
        key = f"rate_limit:fixed:{identifier}:{window_start.timestamp()}"
        
        try:
            if self.redis_client:
                # Redis implementation
                current_count = await self.redis_client.get(key)
                current_count = int(current_count) if current_count else 0
                
                if current_count >= config.requests_per_minute:
                    return RateLimitResult(
                        allowed=False,
                        requests_remaining=0,
                        reset_time=window_start + timedelta(minutes=1),
                        retry_after=60
                    )
                
                # Increment counter with expiration
                pipe = self.redis_client.pipeline()
                pipe.incr(key)
                pipe.expire(key, 60)  # 1 minute TTL
                await pipe.execute()
                
                return RateLimitResult(
                    allowed=True,
                    requests_remaining=config.requests_per_minute - current_count - 1,
                    reset_time=window_start + timedelta(minutes=1)
                )
            else:
                # Local cache fallback
                return await self._local_cache_check(identifier, config, "fixed")
                
        except Exception as e:
            logger.error("Fixed window rate limit check failed", error=str(e))
            # Fail open - allow request but log error
            return RateLimitResult(
                allowed=True,
                requests_remaining=config.requests_per_minute,
                reset_time=now + timedelta(minutes=1)
            )
    
    async def _sliding_window_check(
        self, 
        identifier: str, 
        config: RateLimitConfig
    ) -> RateLimitResult:
        """Sliding window rate limiting using sorted sets"""
        now = time.time()
        window_start = now - 60  # 1 minute window
        
        key = f"rate_limit:sliding:{identifier}"
        
        try:
            if self.redis_client:
                # Remove old entries outside the window
                await self.redis_client.zremrangebyscore(key, "-inf", window_start)
                
                # Count current requests in window
                current_count = await self.redis_client.zcard(key)
                
                if current_count >= config.requests_per_minute:
                    # Get the oldest request in window to calculate retry_after
                    oldest = await self.redis_client.zrange(key, 0, 0, withscores=True)
                    if oldest:
                        retry_after = int(oldest[0][1] + 60 - now)
                    else:
                        retry_after = 60
                        
                    return RateLimitResult(
                        allowed=False,
                        requests_remaining=0,
                        reset_time=datetime.utcfromtimestamp(now + retry_after),
                        retry_after=retry_after
                    )
                
                # Add current request
                pipe = self.redis_client.pipeline()
                pipe.zadd(key, {str(now): now})
                pipe.expire(key, 60)  # Set TTL for cleanup
                await pipe.execute()
                
                return RateLimitResult(
                    allowed=True,
                    requests_remaining=config.requests_per_minute - current_count - 1,
                    reset_time=datetime.utcfromtimestamp(now + 60)
                )
            else:
                # Local cache fallback
                return await self._local_cache_check(identifier, config, "sliding")
                
        except Exception as e:
            logger.error("Sliding window rate limit check failed", error=str(e))
            return RateLimitResult(
                allowed=True,
                requests_remaining=config.requests_per_minute,
                reset_time=datetime.utcnow() + timedelta(minutes=1)
            )
    
    async def _token_bucket_check(
        self, 
        identifier: str, 
        config: RateLimitConfig
    ) -> RateLimitResult:
        """Token bucket rate limiting"""
        now = time.time()
        key = f"rate_limit:token:{identifier}"
        
        try:
            if self.redis_client:
                # Lua script for atomic token bucket operations
                lua_script = """
                local key = KEYS[1]
                local capacity = tonumber(ARGV[1])
                local refill_rate = tonumber(ARGV[2])
                local now = tonumber(ARGV[3])
                
                local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
                local tokens = tonumber(bucket[1]) or capacity
                local last_refill = tonumber(bucket[2]) or now
                
                -- Calculate tokens to add based on time elapsed
                local time_elapsed = now - last_refill
                local tokens_to_add = time_elapsed * refill_rate
                tokens = math.min(capacity, tokens + tokens_to_add)
                
                if tokens < 1 then
                    return {0, tokens, now}
                else
                    tokens = tokens - 1
                    redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
                    redis.call('EXPIRE', key, 3600)  -- 1 hour TTL
                    return {1, tokens, now}
                end
                """
                
                result = await self.redis_client.eval(
                    lua_script,
                    1,
                    key,
                    str(config.bucket_capacity),
                    str(config.refill_rate),
                    str(now)
                )
                
                allowed = bool(result[0])
                remaining_tokens = result[1]
                
                if not allowed:
                    # Calculate retry_after
                    retry_after = int(1.0 / config.refill_rate)
                    return RateLimitResult(
                        allowed=False,
                        requests_remaining=0,
                        reset_time=datetime.utcfromtimestamp(now + retry_after),
                        retry_after=retry_after
                    )
                
                return RateLimitResult(
                    allowed=True,
                    requests_remaining=int(remaining_tokens),
                    reset_time=datetime.utcfromtimestamp(
                        now + (config.bucket_capacity - remaining_tokens) / config.refill_rate
                    )
                )
            else:
                # Local cache fallback
                return await self._local_cache_check(identifier, config, "token")
                
        except Exception as e:
            logger.error("Token bucket rate limit check failed", error=str(e))
            return RateLimitResult(
                allowed=True,
                requests_remaining=config.bucket_capacity,
                reset_time=datetime.utcnow() + timedelta(minutes=1)
            )
    
    async def _leaky_bucket_check(
        self, 
        identifier: str, 
        config: RateLimitConfig
    ) -> RateLimitResult:
        """Leaky bucket rate limiting"""
        now = time.time()
        key = f"rate_limit:leaky:{identifier}"
        
        try:
            if self.redis_client:
                # Lua script for atomic leaky bucket operations
                lua_script = """
                local key = KEYS[1]
                local capacity = tonumber(ARGV[1])
                local leak_rate = tonumber(ARGV[2])
                local now = tonumber(ARGV[3])
                
                local bucket = redis.call('HMGET', key, 'volume', 'last_leak')
                local volume = tonumber(bucket[1]) or 0
                local last_leak = tonumber(bucket[2]) or now
                
                -- Calculate volume to leak based on time elapsed
                local time_elapsed = now - last_leak
                local volume_to_leak = time_elapsed * leak_rate
                volume = math.max(0, volume - volume_to_leak)
                
                if volume >= capacity then
                    return {0, volume, now}
                else
                    volume = volume + 1
                    redis.call('HMSET', key, 'volume', volume, 'last_leak', now)
                    redis.call('EXPIRE', key, 3600)  -- 1 hour TTL
                    return {1, volume, now}
                end
                """
                
                result = await self.redis_client.eval(
                    lua_script,
                    1,
                    key,
                    str(config.bucket_capacity),
                    str(config.leak_rate),
                    str(now)
                )
                
                allowed = bool(result[0])
                current_volume = result[1]
                
                if not allowed:
                    # Calculate retry_after
                    retry_after = int(1.0 / config.leak_rate)
                    return RateLimitResult(
                        allowed=False,
                        requests_remaining=0,
                        reset_time=datetime.utcfromtimestamp(now + retry_after),
                        retry_after=retry_after
                    )
                
                return RateLimitResult(
                    allowed=True,
                    requests_remaining=int(config.bucket_capacity - current_volume),
                    reset_time=datetime.utcfromtimestamp(
                        now + current_volume / config.leak_rate
                    )
                )
            else:
                # Local cache fallback
                return await self._local_cache_check(identifier, config, "leaky")
                
        except Exception as e:
            logger.error("Leaky bucket rate limit check failed", error=str(e))
            return RateLimitResult(
                allowed=True,
                requests_remaining=config.bucket_capacity,
                reset_time=datetime.utcnow() + timedelta(minutes=1)
            )
    
    async def _local_cache_check(
        self, 
        identifier: str, 
        config: RateLimitConfig,
        strategy: str
    ) -> RateLimitResult:
        """Local cache fallback when Redis is unavailable"""
        now = time.time()
        
        if identifier not in self._local_cache:
            self._local_cache[identifier] = {
                "requests": [],
                "tokens": config.bucket_capacity,
                "last_refill": now,
                "volume": 0,
                "last_leak": now
            }
        
        cache_entry = self._local_cache[identifier]
        
        if strategy == "sliding":
            # Remove old requests outside 1-minute window
            cache_entry["requests"] = [
                req_time for req_time in cache_entry["requests"] 
                if now - req_time < 60
            ]
            
            if len(cache_entry["requests"]) >= config.requests_per_minute:
                retry_after = int(cache_entry["requests"][0] + 60 - now)
                return RateLimitResult(
                    allowed=False,
                    requests_remaining=0,
                    reset_time=datetime.utcfromtimestamp(now + retry_after),
                    retry_after=retry_after
                )
            
            cache_entry["requests"].append(now)
            return RateLimitResult(
                allowed=True,
                requests_remaining=config.requests_per_minute - len(cache_entry["requests"]),
                reset_time=datetime.utcfromtimestamp(now + 60)
            )
        
        elif strategy == "token":
            # Refill tokens
            time_elapsed = now - cache_entry["last_refill"]
            tokens_to_add = time_elapsed * config.refill_rate
            cache_entry["tokens"] = min(
                config.bucket_capacity, 
                cache_entry["tokens"] + tokens_to_add
            )
            cache_entry["last_refill"] = now
            
            if cache_entry["tokens"] < 1:
                retry_after = int(1.0 / config.refill_rate)
                return RateLimitResult(
                    allowed=False,
                    requests_remaining=0,
                    reset_time=datetime.utcfromtimestamp(now + retry_after),
                    retry_after=retry_after
                )
            
            cache_entry["tokens"] -= 1
            return RateLimitResult(
                allowed=True,
                requests_remaining=int(cache_entry["tokens"]),
                reset_time=datetime.utcfromtimestamp(
                    now + (config.bucket_capacity - cache_entry["tokens"]) / config.refill_rate
                )
            )
        
        # Default to simple counter for other strategies
        return RateLimitResult(
            allowed=True,
            requests_remaining=config.requests_per_minute,
            reset_time=datetime.utcnow() + timedelta(minutes=1)
        )
    
    async def reset_rate_limit(self, identifier: str):
        """Reset rate limit for identifier (admin function)"""
        try:
            if self.redis_client:
                # Find and delete all rate limit keys for identifier
                pattern = f"rate_limit:*:{identifier}*"
                keys = []
                async for key in self.redis_client.scan_iter(match=pattern):
                    keys.append(key)
                
                if keys:
                    await self.redis_client.delete(*keys)
                    
            # Clear local cache entry
            if identifier in self._local_cache:
                del self._local_cache[identifier]
                
            logger.info("Rate limit reset", identifier=identifier)
            
        except Exception as e:
            logger.error("Failed to reset rate limit", identifier=identifier, error=str(e))
    
    async def get_rate_limit_status(self, identifier: str) -> Dict[str, Union[int, float]]:
        """Get current rate limit status for identifier"""
        try:
            if self.redis_client:
                # Check different strategy keys
                status = {}
                
                # Fixed window
                now = datetime.utcnow().replace(second=0, microsecond=0)
                fixed_key = f"rate_limit:fixed:{identifier}:{now.timestamp()}"
                fixed_count = await self.redis_client.get(fixed_key)
                status["fixed_window_requests"] = int(fixed_count) if fixed_count else 0
                
                # Sliding window
                sliding_key = f"rate_limit:sliding:{identifier}"
                sliding_count = await self.redis_client.zcard(sliding_key)
                status["sliding_window_requests"] = sliding_count
                
                # Token bucket
                token_key = f"rate_limit:token:{identifier}"
                token_data = await self.redis_client.hmget(token_key, "tokens", "last_refill")
                if token_data[0]:
                    status["token_bucket_tokens"] = float(token_data[0])
                    status["token_bucket_last_refill"] = float(token_data[1])
                
                # Leaky bucket
                leaky_key = f"rate_limit:leaky:{identifier}"
                leaky_data = await self.redis_client.hmget(leaky_key, "volume", "last_leak")
                if leaky_data[0]:
                    status["leaky_bucket_volume"] = float(leaky_data[0])
                    status["leaky_bucket_last_leak"] = float(leaky_data[1])
                
                return status
            else:
                # Local cache status
                if identifier in self._local_cache:
                    return {
                        "local_cache_requests": len(self._local_cache[identifier]["requests"]),
                        "local_cache_tokens": self._local_cache[identifier]["tokens"],
                        "local_cache_volume": self._local_cache[identifier]["volume"]
                    }
                else:
                    return {}
                    
        except Exception as e:
            logger.error("Failed to get rate limit status", identifier=identifier, error=str(e))
            return {}