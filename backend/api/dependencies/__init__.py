"""
API Dependencies Package

Contains all dependency injection modules for authentication,
database access, validation, logging, and rate limiting.
"""

from .auth import (
    get_current_user,
    get_current_active_user,
    require_roles,
    require_admin,
    require_trader,
    authenticate_user,
    PasswordHandler,
    JWTHandler,
    BruteForceProtection,
    SessionManager
)

from .database import get_db, get_db_session

from .rate_limiting import (
    limiter,
    rate_limit,
    auth_rate_limit,
    api_rate_limit,
    trading_rate_limit,
    admin_rate_limit
)

from .validation import (
    validate_request_security,
    sanitize_input,
    InputSanitizer,
    SecurityHeaders,
    BusinessLogicValidator,
    PaginationValidator
)

from .logging import (
    audit_logger,
    request_logger,
    compliance_logger,
    privacy_logger,
    AuditLogger,
    RequestLogger,
    ComplianceLogger,
    DataPrivacyLogger
)

__all__ = [
    # Auth
    "get_current_user",
    "get_current_active_user", 
    "require_roles",
    "require_admin",
    "require_trader",
    "authenticate_user",
    "PasswordHandler",
    "JWTHandler",
    "BruteForceProtection",
    "SessionManager",
    
    # Database
    "get_db",
    "get_db_session",
    
    # Rate Limiting
    "limiter",
    "rate_limit",
    "auth_rate_limit",
    "api_rate_limit", 
    "trading_rate_limit",
    "admin_rate_limit",
    
    # Validation
    "validate_request_security",
    "sanitize_input",
    "InputSanitizer",
    "SecurityHeaders",
    "BusinessLogicValidator",
    "PaginationValidator",
    
    # Logging
    "audit_logger",
    "request_logger",
    "compliance_logger",
    "privacy_logger",
    "AuditLogger",
    "RequestLogger", 
    "ComplianceLogger",
    "DataPrivacyLogger",
]