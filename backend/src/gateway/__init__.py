"""
Qenergyz API Gateway / Backend-for-Frontend (BFF) Service

This module provides the API Gateway that orchestrates communication 
between the React frontend and backend services with:
- Rate limiting and DDoS protection
- OAuth/SSO integration
- Request/response transformation
- Circuit breakers for fault tolerance
- Audit logging and security monitoring
"""

from .bff import QenergyZBFF
from .rate_limiter import RateLimiter, RateLimitConfig
from .circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from .oauth_provider import OAuthProvider, OAuthConfig
from .security_middleware import SecurityMiddleware
from .audit_logger import AuditLogger

__all__ = [
    "QenergyZBFF",
    "RateLimiter", 
    "RateLimitConfig",
    "CircuitBreaker",
    "CircuitBreakerConfig", 
    "OAuthProvider",
    "OAuthConfig",
    "SecurityMiddleware",
    "AuditLogger"
]