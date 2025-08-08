"""
Validation Dependencies

Input validation, sanitization, and data integrity checks.
"""

import re
import html
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status, Request
from pydantic import BaseModel, validator, Field
import bleach
import structlog

from ..utils.config import get_settings


logger = structlog.get_logger(__name__)
settings = get_settings()


class ValidationError(HTTPException):
    """Validation error exception"""
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail
        )


class InputSanitizer:
    """Input sanitization utilities"""
    
    # Allowed HTML tags for rich text
    ALLOWED_TAGS = [
        'p', 'br', 'strong', 'em', 'u', 'ul', 'ol', 'li',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote'
    ]
    
    # Allowed HTML attributes
    ALLOWED_ATTRIBUTES = {
        '*': ['class'],
        'a': ['href', 'title'],
        'blockquote': ['cite']
    }
    
    @staticmethod
    def sanitize_html(text: str) -> str:
        """Sanitize HTML content"""
        if not text:
            return text
        
        return bleach.clean(
            text,
            tags=InputSanitizer.ALLOWED_TAGS,
            attributes=InputSanitizer.ALLOWED_ATTRIBUTES,
            strip=True
        )
    
    @staticmethod
    def sanitize_text(text: str) -> str:
        """Sanitize plain text"""
        if not text:
            return text
        
        # Remove HTML entities and tags
        text = html.escape(text)
        
        # Remove potential script injections
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
        text = re.sub(r'on\w+\s*=', '', text, flags=re.IGNORECASE)
        
        return text.strip()
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename for safe storage"""
        if not filename:
            return filename
        
        # Remove dangerous characters
        filename = re.sub(r'[^a-zA-Z0-9\-_\.]', '_', filename)
        
        # Prevent directory traversal
        filename = filename.replace('..', '_')
        
        # Limit length
        if len(filename) > 255:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            filename = name[:250] + ('.' + ext if ext else '')
        
        return filename
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        if not email:
            return False
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """Validate phone number format"""
        if not phone:
            return False
        
        # Remove all non-digit characters
        digits = re.sub(r'\D', '', phone)
        
        # Check length (between 7 and 15 digits)
        return 7 <= len(digits) <= 15
    
    @staticmethod
    def validate_password_strength(password: str) -> Dict[str, Any]:
        """Validate password strength"""
        if not password:
            return {"valid": False, "errors": ["Password is required"]}
        
        errors = []
        
        # Length check
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long")
        
        if len(password) > 128:
            errors.append("Password must be less than 128 characters long")
        
        # Complexity checks
        if not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        
        if not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        
        if not re.search(r'\d', password):
            errors.append("Password must contain at least one digit")
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")
        
        # Common password check
        common_passwords = [
            'password', '123456', '123456789', 'qwerty', 'abc123',
            'password123', 'admin', 'letmein', 'welcome', 'monkey'
        ]
        
        if password.lower() in common_passwords:
            errors.append("Password is too common")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "strength": "strong" if len(errors) == 0 else "weak"
        }


class SecurityHeaders:
    """Security header validation and enforcement"""
    
    @staticmethod
    def validate_content_type(request: Request, allowed_types: List[str] = None):
        """Validate request content type"""
        if not allowed_types:
            allowed_types = ['application/json', 'multipart/form-data']
        
        content_type = request.headers.get('content-type', '').split(';')[0].strip()
        
        if content_type and content_type not in allowed_types:
            raise ValidationError(
                f"Invalid content type: {content_type}. Allowed: {', '.join(allowed_types)}"
            )
    
    @staticmethod
    def validate_user_agent(request: Request):
        """Validate user agent header"""
        user_agent = request.headers.get('user-agent', '')
        
        if not user_agent:
            logger.warning("Request without user agent", ip=request.client.host if request.client else "unknown")
        
        # Block known bad user agents
        blocked_agents = [
            'sqlmap', 'nikto', 'nessus', 'openvas', 'nmap',
            'masscan', 'zap', 'burp', 'scanner'
        ]
        
        user_agent_lower = user_agent.lower()
        for blocked in blocked_agents:
            if blocked in user_agent_lower:
                raise ValidationError("Blocked user agent")
    
    @staticmethod
    def check_request_size(request: Request, max_size: int = 10 * 1024 * 1024):  # 10MB default
        """Check request size limits"""
        content_length = request.headers.get('content-length')
        
        if content_length:
            try:
                size = int(content_length)
                if size > max_size:
                    raise ValidationError(
                        f"Request too large: {size} bytes (max: {max_size} bytes)"
                    )
            except ValueError:
                raise ValidationError("Invalid content-length header")


class BusinessLogicValidator:
    """Business logic validation"""
    
    @staticmethod
    def validate_trade_amount(amount: float, min_amount: float = 1.0, max_amount: float = 1000000.0):
        """Validate trading amount"""
        if amount <= 0:
            raise ValidationError("Trade amount must be positive")
        
        if amount < min_amount:
            raise ValidationError(f"Trade amount must be at least {min_amount}")
        
        if amount > max_amount:
            raise ValidationError(f"Trade amount cannot exceed {max_amount}")
        
        # Check for reasonable decimal places (max 8)
        if len(str(amount).split('.')[-1]) > 8:
            raise ValidationError("Trade amount has too many decimal places")
    
    @staticmethod
    def validate_date_range(start_date, end_date, max_days: int = 365):
        """Validate date range"""
        if start_date >= end_date:
            raise ValidationError("Start date must be before end date")
        
        days_diff = (end_date - start_date).days
        if days_diff > max_days:
            raise ValidationError(f"Date range cannot exceed {max_days} days")
    
    @staticmethod
    def validate_compliance_region(region: str):
        """Validate compliance region"""
        allowed_regions = ['middle_east', 'usa', 'uk', 'europe', 'guyana']
        
        if region not in allowed_regions:
            raise ValidationError(
                f"Invalid region: {region}. Allowed: {', '.join(allowed_regions)}"
            )


async def validate_request_security(request: Request):
    """Comprehensive request security validation"""
    security = SecurityHeaders()
    
    # Validate user agent
    security.validate_user_agent(request)
    
    # Check request size
    security.check_request_size(request)
    
    # Log suspicious requests
    suspicious_headers = [
        'x-forwarded-for', 'x-real-ip', 'x-cluster-client-ip',
        'x-forwarded', 'forwarded-for', 'forwarded'
    ]
    
    for header in suspicious_headers:
        if header in request.headers:
            logger.warning(
                "Suspicious header detected",
                header=header,
                value=request.headers[header],
                ip=request.client.host if request.client else "unknown"
            )


def sanitize_input(data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize input data"""
    if not isinstance(data, dict):
        return data
    
    sanitized = {}
    sanitizer = InputSanitizer()
    
    for key, value in data.items():
        if isinstance(value, str):
            sanitized[key] = sanitizer.sanitize_text(value)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_input(value)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_input(item) if isinstance(item, dict) else
                sanitizer.sanitize_text(item) if isinstance(item, str) else item
                for item in value
            ]
        else:
            sanitized[key] = value
    
    return sanitized


class PaginationValidator(BaseModel):
    """Pagination parameters validation"""
    page: int = Field(1, ge=1, le=1000, description="Page number")
    size: int = Field(20, ge=1, le=100, description="Page size")
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size
    
    @property
    def limit(self) -> int:
        return self.size