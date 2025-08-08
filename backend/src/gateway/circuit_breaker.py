"""
Circuit Breaker for API Gateway

Implements the circuit breaker pattern to prevent cascading failures
and provide fault tolerance for downstream services.
"""

import asyncio
import time
from typing import Dict, Optional, Callable, Any
from datetime import datetime, timedelta
from enum import Enum
import structlog
from pydantic import BaseModel, Field
import redis.asyncio as aioredis

from ..config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class CircuitState(str, Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"         # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration"""
    failure_threshold: int = Field(default=5, ge=1, description="Failures before opening")
    success_threshold: int = Field(default=3, ge=1, description="Successes to close from half-open")
    timeout: int = Field(default=60, ge=1, description="Seconds before trying half-open")
    
    # Advanced configuration
    slow_call_duration_threshold: float = Field(default=5.0, ge=0.1, description="Seconds to consider slow")
    slow_call_rate_threshold: float = Field(default=0.8, ge=0.1, le=1.0, description="Slow call rate threshold")
    minimum_number_of_calls: int = Field(default=10, ge=1, description="Minimum calls before evaluating")
    sliding_window_size: int = Field(default=100, ge=10, description="Sliding window size")
    
    # Monitoring
    max_wait_duration_in_half_open: int = Field(default=30, ge=1, description="Max wait in half-open state")


class CircuitBreakerStats(BaseModel):
    """Circuit breaker statistics"""
    state: CircuitState
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    total_requests: int = 0
    failed_requests: int = 0
    slow_requests: int = 0
    average_response_time: float = 0.0
    next_attempt_time: Optional[datetime] = None


class CircuitBreakerException(Exception):
    """Exception raised when circuit breaker is open"""
    
    def __init__(self, service_name: str, retry_after: int):
        self.service_name = service_name
        self.retry_after = retry_after
        super().__init__(f"Circuit breaker is open for service '{service_name}'. Retry after {retry_after} seconds.")


class CircuitBreaker:
    """
    Advanced Circuit Breaker with multiple failure detection strategies
    
    Features:
    - Failure rate and slow call rate detection
    - Sliding window for statistics
    - Half-open state testing
    - Redis-backed persistence for distributed systems
    """
    
    def __init__(self, redis_client: Optional[aioredis.Redis] = None):
        self.redis_client = redis_client
        self._circuits: Dict[str, CircuitBreakerStats] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        
        # Default configurations per service type
        self.default_configs = {
            "trading": CircuitBreakerConfig(
                failure_threshold=3,
                timeout=30,
                slow_call_duration_threshold=2.0
            ),
            "risk": CircuitBreakerConfig(
                failure_threshold=5,
                timeout=60,
                slow_call_duration_threshold=5.0
            ),
            "compliance": CircuitBreakerConfig(
                failure_threshold=10,
                timeout=120,
                slow_call_duration_threshold=10.0
            ),
            "iot": CircuitBreakerConfig(
                failure_threshold=8,
                timeout=45,
                slow_call_duration_threshold=3.0
            ),
            "default": CircuitBreakerConfig()
        }
    
    async def initialize(self, redis_client: aioredis.Redis):
        """Initialize circuit breaker with Redis client"""
        self.redis_client = redis_client
        try:
            await self.redis_client.ping()
            logger.info("Circuit breaker initialized with Redis")
        except Exception as e:
            logger.warning("Circuit breaker falling back to local state", error=str(e))
    
    def _get_lock(self, service_name: str) -> asyncio.Lock:
        """Get or create lock for service"""
        if service_name not in self._locks:
            self._locks[service_name] = asyncio.Lock()
        return self._locks[service_name]
    
    async def _get_circuit_stats(self, service_name: str) -> CircuitBreakerStats:
        """Get circuit breaker stats from Redis or local cache"""
        try:
            if self.redis_client:
                key = f"circuit_breaker:{service_name}"
                data = await self.redis_client.hgetall(key)
                
                if data:
                    return CircuitBreakerStats(
                        state=CircuitState(data.get("state", CircuitState.CLOSED)),
                        failure_count=int(data.get("failure_count", 0)),
                        success_count=int(data.get("success_count", 0)),
                        last_failure_time=datetime.fromisoformat(data["last_failure_time"]) 
                            if data.get("last_failure_time") else None,
                        last_success_time=datetime.fromisoformat(data["last_success_time"])
                            if data.get("last_success_time") else None,
                        total_requests=int(data.get("total_requests", 0)),
                        failed_requests=int(data.get("failed_requests", 0)),
                        slow_requests=int(data.get("slow_requests", 0)),
                        average_response_time=float(data.get("average_response_time", 0.0)),
                        next_attempt_time=datetime.fromisoformat(data["next_attempt_time"])
                            if data.get("next_attempt_time") else None
                    )
        except Exception as e:
            logger.warning("Failed to get circuit stats from Redis", service=service_name, error=str(e))
        
        # Return local cache or create new
        if service_name not in self._circuits:
            self._circuits[service_name] = CircuitBreakerStats(state=CircuitState.CLOSED)
        
        return self._circuits[service_name]
    
    async def _save_circuit_stats(self, service_name: str, stats: CircuitBreakerStats):
        """Save circuit breaker stats to Redis and local cache"""
        self._circuits[service_name] = stats
        
        try:
            if self.redis_client:
                key = f"circuit_breaker:{service_name}"
                data = {
                    "state": stats.state.value,
                    "failure_count": str(stats.failure_count),
                    "success_count": str(stats.success_count),
                    "total_requests": str(stats.total_requests),
                    "failed_requests": str(stats.failed_requests),
                    "slow_requests": str(stats.slow_requests),
                    "average_response_time": str(stats.average_response_time)
                }
                
                if stats.last_failure_time:
                    data["last_failure_time"] = stats.last_failure_time.isoformat()
                if stats.last_success_time:
                    data["last_success_time"] = stats.last_success_time.isoformat()
                if stats.next_attempt_time:
                    data["next_attempt_time"] = stats.next_attempt_time.isoformat()
                
                await self.redis_client.hset(key, mapping=data)
                await self.redis_client.expire(key, 86400)  # 24 hour TTL
                
        except Exception as e:
            logger.warning("Failed to save circuit stats to Redis", service=service_name, error=str(e))
    
    def can_proceed(self, service_name: str, config: Optional[CircuitBreakerConfig] = None) -> bool:
        """
        Check if request can proceed (synchronous check)
        
        Args:
            service_name: Name of the service
            config: Circuit breaker configuration
            
        Returns:
            True if request can proceed, False otherwise
        """
        if config is None:
            config = self.default_configs.get(service_name, self.default_configs["default"])
        
        # Get current stats (use local cache for sync check)
        if service_name not in self._circuits:
            return True
        
        stats = self._circuits[service_name]
        now = datetime.utcnow()
        
        if stats.state == CircuitState.CLOSED:
            return True
        elif stats.state == CircuitState.OPEN:
            # Check if timeout period has elapsed
            if stats.next_attempt_time and now >= stats.next_attempt_time:
                # Should transition to half-open, but we'll do this in async method
                return True
            return False
        elif stats.state == CircuitState.HALF_OPEN:
            # Allow limited requests in half-open state
            return stats.success_count < config.success_threshold
        
        return True
    
    async def call_with_circuit_breaker(
        self,
        service_name: str,
        func: Callable,
        *args,
        config: Optional[CircuitBreakerConfig] = None,
        **kwargs
    ) -> Any:
        """
        Execute function with circuit breaker protection
        
        Args:
            service_name: Name of the service
            func: Function to call
            config: Circuit breaker configuration
            *args, **kwargs: Arguments for the function
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerException: If circuit is open
        """
        if config is None:
            config = self.default_configs.get(service_name, self.default_configs["default"])
        
        async with self._get_lock(service_name):
            stats = await self._get_circuit_stats(service_name)
            
            # Check if we can proceed
            if not await self._can_proceed_async(service_name, stats, config):
                retry_after = config.timeout
                if stats.next_attempt_time:
                    retry_after = int((stats.next_attempt_time - datetime.utcnow()).total_seconds())
                raise CircuitBreakerException(service_name, retry_after)
            
            # Execute the function with timing
            start_time = time.time()
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                end_time = time.time()
                response_time = end_time - start_time
                
                # Record success
                await self._record_success(service_name, stats, config, response_time)
                return result
                
            except Exception as e:
                end_time = time.time()
                response_time = end_time - start_time
                
                # Record failure
                await self._record_failure(service_name, stats, config, response_time)
                raise
    
    async def _can_proceed_async(
        self, 
        service_name: str, 
        stats: CircuitBreakerStats, 
        config: CircuitBreakerConfig
    ) -> bool:
        """Async version of can_proceed with state transitions"""
        now = datetime.utcnow()
        
        if stats.state == CircuitState.CLOSED:
            # Check if we should open due to failure rate
            if stats.total_requests >= config.minimum_number_of_calls:
                failure_rate = stats.failed_requests / stats.total_requests
                slow_rate = stats.slow_requests / stats.total_requests
                
                if (failure_rate >= 0.5 or  # 50% failure rate threshold
                    slow_rate >= config.slow_call_rate_threshold):
                    
                    await self._transition_to_open(service_name, stats, config)
                    return False
            
            return True
            
        elif stats.state == CircuitState.OPEN:
            # Check if timeout period has elapsed
            if stats.next_attempt_time and now >= stats.next_attempt_time:
                await self._transition_to_half_open(service_name, stats, config)
                return True
            return False
            
        elif stats.state == CircuitState.HALF_OPEN:
            # Allow limited requests in half-open state
            return stats.success_count < config.success_threshold
        
        return True
    
    async def _record_success(
        self, 
        service_name: str, 
        stats: CircuitBreakerStats, 
        config: CircuitBreakerConfig,
        response_time: float
    ):
        """Record successful request"""
        now = datetime.utcnow()
        
        stats.success_count += 1
        stats.total_requests += 1
        stats.last_success_time = now
        
        # Update average response time
        if stats.total_requests == 1:
            stats.average_response_time = response_time
        else:
            stats.average_response_time = (
                (stats.average_response_time * (stats.total_requests - 1) + response_time) 
                / stats.total_requests
            )
        
        # Check if it's a slow call
        if response_time > config.slow_call_duration_threshold:
            stats.slow_requests += 1
        
        # State transitions
        if stats.state == CircuitState.HALF_OPEN:
            if stats.success_count >= config.success_threshold:
                await self._transition_to_closed(service_name, stats, config)
        
        # Sliding window management (simplified)
        if stats.total_requests > config.sliding_window_size:
            await self._apply_sliding_window(service_name, stats, config)
        
        await self._save_circuit_stats(service_name, stats)
        
        logger.debug("Circuit breaker success recorded",
                    service=service_name,
                    state=stats.state,
                    response_time=response_time)
    
    async def _record_failure(
        self, 
        service_name: str, 
        stats: CircuitBreakerStats, 
        config: CircuitBreakerConfig,
        response_time: float
    ):
        """Record failed request"""
        now = datetime.utcnow()
        
        stats.failure_count += 1
        stats.total_requests += 1
        stats.failed_requests += 1
        stats.last_failure_time = now
        
        # Update average response time
        if stats.total_requests == 1:
            stats.average_response_time = response_time
        else:
            stats.average_response_time = (
                (stats.average_response_time * (stats.total_requests - 1) + response_time)
                / stats.total_requests
            )
        
        # State transitions
        if stats.state == CircuitState.CLOSED:
            if stats.failure_count >= config.failure_threshold:
                await self._transition_to_open(service_name, stats, config)
        elif stats.state == CircuitState.HALF_OPEN:
            await self._transition_to_open(service_name, stats, config)
        
        # Sliding window management
        if stats.total_requests > config.sliding_window_size:
            await self._apply_sliding_window(service_name, stats, config)
        
        await self._save_circuit_stats(service_name, stats)
        
        logger.warning("Circuit breaker failure recorded",
                      service=service_name,
                      state=stats.state,
                      failure_count=stats.failure_count,
                      response_time=response_time)
    
    async def _transition_to_open(
        self, 
        service_name: str, 
        stats: CircuitBreakerStats, 
        config: CircuitBreakerConfig
    ):
        """Transition circuit to OPEN state"""
        stats.state = CircuitState.OPEN
        stats.next_attempt_time = datetime.utcnow() + timedelta(seconds=config.timeout)
        
        logger.warning("Circuit breaker opened",
                      service=service_name,
                      failure_count=stats.failure_count,
                      next_attempt=stats.next_attempt_time)
        
        # Send alert
        await self._send_circuit_alert(service_name, "OPENED", stats)
    
    async def _transition_to_half_open(
        self, 
        service_name: str, 
        stats: CircuitBreakerStats, 
        config: CircuitBreakerConfig
    ):
        """Transition circuit to HALF_OPEN state"""
        stats.state = CircuitState.HALF_OPEN
        stats.success_count = 0
        stats.failure_count = 0
        stats.next_attempt_time = None
        
        logger.info("Circuit breaker half-opened", service=service_name)
        
        # Send alert
        await self._send_circuit_alert(service_name, "HALF_OPENED", stats)
    
    async def _transition_to_closed(
        self, 
        service_name: str, 
        stats: CircuitBreakerStats, 
        config: CircuitBreakerConfig
    ):
        """Transition circuit to CLOSED state"""
        stats.state = CircuitState.CLOSED
        stats.success_count = 0
        stats.failure_count = 0
        stats.next_attempt_time = None
        
        logger.info("Circuit breaker closed", service=service_name)
        
        # Send alert
        await self._send_circuit_alert(service_name, "CLOSED", stats)
    
    async def _apply_sliding_window(
        self, 
        service_name: str, 
        stats: CircuitBreakerStats, 
        config: CircuitBreakerConfig
    ):
        """Apply sliding window to stats (simplified implementation)"""
        # In a real implementation, you'd maintain a more sophisticated
        # sliding window with timestamps. For now, we'll just reset
        # when we exceed the window size.
        
        reduction_factor = 0.8  # Reduce stats by 20%
        stats.total_requests = int(stats.total_requests * reduction_factor)
        stats.failed_requests = int(stats.failed_requests * reduction_factor)
        stats.slow_requests = int(stats.slow_requests * reduction_factor)
        
        logger.debug("Applied sliding window reduction", service=service_name)
    
    async def _send_circuit_alert(self, service_name: str, event: str, stats: CircuitBreakerStats):
        """Send circuit breaker alert (placeholder for actual implementation)"""
        alert_data = {
            "service": service_name,
            "event": event,
            "state": stats.state.value,
            "failure_count": stats.failure_count,
            "success_count": stats.success_count,
            "total_requests": stats.total_requests,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # In a real implementation, you'd send this to an alerting system
        logger.info("Circuit breaker alert", **alert_data)
    
    async def record_success(self, service_name: str):
        """Record successful request (public method)"""
        async with self._get_lock(service_name):
            config = self.default_configs.get(service_name, self.default_configs["default"])
            stats = await self._get_circuit_stats(service_name)
            await self._record_success(service_name, stats, config, 0.0)
    
    async def record_failure(self, service_name: str):
        """Record failed request (public method)"""
        async with self._get_lock(service_name):
            config = self.default_configs.get(service_name, self.default_configs["default"])
            stats = await self._get_circuit_stats(service_name)
            await self._record_failure(service_name, stats, config, 0.0)
    
    def get_circuit_stats(self, service_name: str) -> Optional[CircuitBreakerStats]:
        """Get circuit breaker stats (synchronous)"""
        return self._circuits.get(service_name)
    
    async def reset_circuit(self, service_name: str):
        """Reset circuit breaker (admin function)"""
        async with self._get_lock(service_name):
            stats = CircuitBreakerStats(state=CircuitState.CLOSED)
            await self._save_circuit_stats(service_name, stats)
            
            logger.info("Circuit breaker reset", service=service_name)
    
    async def get_all_circuits_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers"""
        try:
            status = {}
            
            # Get from Redis if available
            if self.redis_client:
                pattern = "circuit_breaker:*"
                async for key in self.redis_client.scan_iter(match=pattern):
                    service_name = key.split(":")[-1]
                    stats = await self._get_circuit_stats(service_name)
                    
                    status[service_name] = {
                        "state": stats.state.value,
                        "failure_count": stats.failure_count,
                        "success_count": stats.success_count,
                        "total_requests": stats.total_requests,
                        "failed_requests": stats.failed_requests,
                        "slow_requests": stats.slow_requests,
                        "average_response_time": stats.average_response_time,
                        "last_failure_time": stats.last_failure_time.isoformat() if stats.last_failure_time else None,
                        "last_success_time": stats.last_success_time.isoformat() if stats.last_success_time else None,
                        "next_attempt_time": stats.next_attempt_time.isoformat() if stats.next_attempt_time else None
                    }
            else:
                # Use local cache
                for service_name, stats in self._circuits.items():
                    status[service_name] = {
                        "state": stats.state.value,
                        "failure_count": stats.failure_count,
                        "success_count": stats.success_count,
                        "total_requests": stats.total_requests,
                        "failed_requests": stats.failed_requests,
                        "slow_requests": stats.slow_requests,
                        "average_response_time": stats.average_response_time
                    }
            
            return status
            
        except Exception as e:
            logger.error("Failed to get circuit breaker status", error=str(e))
            return {}