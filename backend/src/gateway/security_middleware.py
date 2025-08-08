"""
Security Middleware for API Gateway

Implements comprehensive security controls:
- CORS (Cross-Origin Resource Sharing)
- CSRF (Cross-Site Request Forgery) protection
- Security headers
- Cookie handling and session security
- Request validation and sanitization
- Content Security Policy (CSP)
"""

import asyncio
import secrets
import hashlib
import hmac
from typing import Dict, List, Optional, Callable, Any, Tuple
from datetime import datetime, timedelta
from urllib.parse import urlparse
import structlog
from fastapi import Request, Response, HTTPException, status
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send
import redis.asyncio as aioredis

from ..config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class SecurityConfig:
    """Security configuration"""
    
    def __init__(self):
        # CORS Configuration
        self.cors_allow_origins = getattr(settings, 'cors_allow_origins', ['*'])
        self.cors_allow_methods = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH']
        self.cors_allow_headers = ['*']
        self.cors_allow_credentials = True
        self.cors_max_age = 86400  # 24 hours
        
        # CSRF Configuration
        self.csrf_token_key = "X-CSRF-Token"
        self.csrf_cookie_name = "csrftoken"
        self.csrf_cookie_max_age = 3600  # 1 hour
        self.csrf_safe_methods = {'GET', 'HEAD', 'OPTIONS', 'TRACE'}
        
        # Security Headers
        self.security_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Permissions-Policy': 'geolocation=(), microphone=(), camera=(), payment=()',
        }
        
        # Content Security Policy
        self.csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' *.googleapis.com *.gstatic.com; "
            "style-src 'self' 'unsafe-inline' *.googleapis.com; "
            "img-src 'self' data: *.googleapis.com *.gstatic.com; "
            "font-src 'self' *.googleapis.com *.gstatic.com; "
            "connect-src 'self' *.googleapis.com wss: ws:; "
            "frame-ancestors 'none'; "
            "object-src 'none'; "
            "base-uri 'self'"
        )
        
        # Cookie Security
        self.cookie_secure = True
        self.cookie_httponly = True
        self.cookie_samesite = "lax"
        
        # Rate Limiting (integrated with main rate limiter)
        self.enable_rate_limiting = True
        self.rate_limit_per_minute = 100
        
        # Request Validation
        self.max_request_size = 10 * 1024 * 1024  # 10MB
        self.blocked_user_agents = [
            'sqlmap', 'nikto', 'nmap', 'masscan', 'zap',
            'burpsuite', 'dirb', 'dirbuster', 'gobuster'
        ]
        
        # IP Filtering
        self.blocked_ips: List[str] = []
        self.allowed_ips: List[str] = []  # If not empty, only these IPs are allowed


class CSRFProtection:
    """CSRF protection implementation"""
    
    def __init__(self, config: SecurityConfig, redis_client: Optional[aioredis.Redis] = None):
        self.config = config
        self.redis_client = redis_client
        self._tokens: Dict[str, Tuple[str, datetime]] = {}  # Fallback storage
    
    def generate_csrf_token(self, session_id: str) -> str:
        """Generate CSRF token for session"""
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(seconds=self.config.csrf_cookie_max_age)
        
        # Store token
        if self.redis_client:
            asyncio.create_task(self._store_token_redis(session_id, token, expires_at))
        else:
            self._tokens[session_id] = (token, expires_at)
        
        return token
    
    async def _store_token_redis(self, session_id: str, token: str, expires_at: datetime):
        """Store CSRF token in Redis"""
        try:
            key = f"csrf:{session_id}"
            data = {
                "token": token,
                "expires_at": expires_at.isoformat()
            }
            await self.redis_client.hset(key, mapping=data)
            await self.redis_client.expire(key, self.config.csrf_cookie_max_age)
        except Exception as e:
            logger.warning("Failed to store CSRF token in Redis", error=str(e))
    
    async def validate_csrf_token(self, session_id: str, provided_token: str) -> bool:
        """Validate CSRF token"""
        try:
            # Get stored token
            if self.redis_client:
                key = f"csrf:{session_id}"
                data = await self.redis_client.hgetall(key)
                if not data:
                    return False
                
                stored_token = data.get("token")
                expires_at_str = data.get("expires_at")
                
                if not stored_token or not expires_at_str:
                    return False
                
                expires_at = datetime.fromisoformat(expires_at_str)
                if datetime.utcnow() > expires_at:
                    await self.redis_client.delete(key)
                    return False
            else:
                # Use local storage
                if session_id not in self._tokens:
                    return False
                
                stored_token, expires_at = self._tokens[session_id]
                if datetime.utcnow() > expires_at:
                    del self._tokens[session_id]
                    return False
            
            # Compare tokens using constant-time comparison
            return hmac.compare_digest(stored_token, provided_token)
            
        except Exception as e:
            logger.warning("CSRF token validation failed", error=str(e))
            return False
    
    def cleanup_expired_tokens(self):
        """Clean up expired tokens from local storage"""
        now = datetime.utcnow()
        expired_sessions = [
            session_id for session_id, (_, expires_at) in self._tokens.items()
            if now > expires_at
        ]
        
        for session_id in expired_sessions:
            del self._tokens[session_id]


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive security middleware
    
    Implements CORS, CSRF, security headers, and request validation.
    """
    
    def __init__(self, app: ASGIApp, config: Optional[SecurityConfig] = None):
        super().__init__(app)
        self.config = config or SecurityConfig()
        self.csrf = CSRFProtection(self.config)
        
        # Compile blocked patterns for performance
        self._blocked_user_agents_lower = [ua.lower() for ua in self.config.blocked_user_agents]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Main security middleware dispatcher"""
        try:
            # Pre-request security checks
            await self._validate_request(request)
            
            # Handle CORS preflight
            if request.method == "OPTIONS":
                return await self._handle_cors_preflight(request)
            
            # CSRF protection
            await self._check_csrf_protection(request)
            
            # Process request
            response = await call_next(request)
            
            # Post-request security enhancements
            await self._enhance_response_security(request, response)
            
            return response
            
        except HTTPException as e:
            return JSONResponse(
                status_code=e.status_code,
                content={"error": e.detail},
                headers=self._get_security_headers()
            )
        except Exception as e:
            logger.error("Security middleware error", error=str(e))
            return JSONResponse(
                status_code=500,
                content={"error": "Internal security error"},
                headers=self._get_security_headers()
            )
    
    async def _validate_request(self, request: Request):
        """Validate incoming request"""
        
        # Check request size
        content_length = request.headers.get('content-length')
        if content_length and int(content_length) > self.config.max_request_size:
            logger.warning("Request too large", size=content_length, 
                          client_ip=self._get_client_ip(request))
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Request too large"
            )
        
        # Check User-Agent
        user_agent = request.headers.get('user-agent', '').lower()
        for blocked_ua in self._blocked_user_agents_lower:
            if blocked_ua in user_agent:
                logger.warning("Blocked user agent detected", user_agent=user_agent,
                              client_ip=self._get_client_ip(request))
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Forbidden"
                )
        
        # IP filtering
        client_ip = self._get_client_ip(request)
        
        # Check blocked IPs
        if client_ip in self.config.blocked_ips:
            logger.warning("Blocked IP attempted access", ip=client_ip)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Check allowed IPs (if allowlist is configured)
        if self.config.allowed_ips and client_ip not in self.config.allowed_ips:
            logger.warning("Non-whitelisted IP attempted access", ip=client_ip)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address considering proxies"""
        # Check X-Forwarded-For header (for proxies)
        forwarded_for = request.headers.get('x-forwarded-for')
        if forwarded_for:
            # Take the first IP (original client)
            return forwarded_for.split(',')[0].strip()
        
        # Check X-Real-IP header (nginx)
        real_ip = request.headers.get('x-real-ip')
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        return request.client.host if request.client else "unknown"
    
    async def _handle_cors_preflight(self, request: Request) -> Response:
        """Handle CORS preflight requests"""
        origin = request.headers.get('origin')
        
        # Check if origin is allowed
        if not self._is_origin_allowed(origin):
            return JSONResponse(
                status_code=403,
                content={"error": "Origin not allowed"}
            )
        
        headers = {
            'Access-Control-Allow-Origin': origin or '*',
            'Access-Control-Allow-Methods': ', '.join(self.config.cors_allow_methods),
            'Access-Control-Allow-Headers': ', '.join(self.config.cors_allow_headers),
            'Access-Control-Max-Age': str(self.config.cors_max_age),
        }
        
        if self.config.cors_allow_credentials:
            headers['Access-Control-Allow-Credentials'] = 'true'
        
        # Add security headers
        headers.update(self._get_security_headers())
        
        return Response(status_code=200, headers=headers)
    
    def _is_origin_allowed(self, origin: Optional[str]) -> bool:
        """Check if origin is allowed"""
        if not origin:
            return True  # Same-origin requests
        
        if '*' in self.config.cors_allow_origins:
            return True
        
        return origin in self.config.cors_allow_origins
    
    async def _check_csrf_protection(self, request: Request):
        """Check CSRF protection for state-changing requests"""
        if request.method in self.config.csrf_safe_methods:
            return  # Safe methods don't need CSRF protection
        
        # Skip CSRF for API requests with proper authentication
        # (assuming API tokens are used instead of cookies)
        auth_header = request.headers.get('authorization')
        if auth_header and auth_header.startswith('Bearer '):
            return
        
        # Get session ID (from cookie or header)
        session_id = self._get_session_id(request)
        if not session_id:
            logger.warning("No session ID for CSRF check", 
                          client_ip=self._get_client_ip(request))
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF protection: No session"
            )
        
        # Get CSRF token from header or form data
        csrf_token = request.headers.get(self.config.csrf_token_key)
        if not csrf_token and request.method == 'POST':
            # Try to get from form data
            try:
                form_data = await request.form()
                csrf_token = form_data.get('csrf_token')
            except Exception:
                pass
        
        if not csrf_token:
            logger.warning("Missing CSRF token", session_id=session_id,
                          client_ip=self._get_client_ip(request))
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF protection: Missing token"
            )
        
        # Validate CSRF token
        if not await self.csrf.validate_csrf_token(session_id, csrf_token):
            logger.warning("Invalid CSRF token", session_id=session_id,
                          client_ip=self._get_client_ip(request))
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF protection: Invalid token"
            )
    
    def _get_session_id(self, request: Request) -> Optional[str]:
        """Get session ID from request"""
        # Try cookie first
        session_cookie = request.cookies.get('session_id')
        if session_cookie:
            return session_cookie
        
        # Try custom header
        return request.headers.get('X-Session-ID')
    
    async def _enhance_response_security(self, request: Request, response: Response):
        """Enhance response with security features"""
        
        # Add security headers
        security_headers = self._get_security_headers()
        for header, value in security_headers.items():
            response.headers[header] = value
        
        # Add CORS headers
        origin = request.headers.get('origin')
        if origin and self._is_origin_allowed(origin):
            response.headers['Access-Control-Allow-Origin'] = origin
            if self.config.cors_allow_credentials:
                response.headers['Access-Control-Allow-Credentials'] = 'true'
        elif not origin:
            response.headers['Access-Control-Allow-Origin'] = '*'
        
        # Set CSRF cookie if needed
        session_id = self._get_session_id(request)
        if session_id and request.method in ['GET', 'HEAD']:
            csrf_token = self.csrf.generate_csrf_token(session_id)
            response.set_cookie(
                key=self.config.csrf_cookie_name,
                value=csrf_token,
                max_age=self.config.csrf_cookie_max_age,
                secure=self.config.cookie_secure,
                httponly=False,  # CSRF token needs to be accessible to JS
                samesite=self.config.cookie_samesite
            )
        
        # Secure session cookie if present
        if 'Set-Cookie' in response.headers:
            self._secure_session_cookie(response)
    
    def _get_security_headers(self) -> Dict[str, str]:
        """Get security headers"""
        headers = self.config.security_headers.copy()
        
        # Add CSP header
        headers['Content-Security-Policy'] = self.config.csp_policy
        
        # Add additional headers based on environment
        if settings.environment == "production":
            headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        return headers
    
    def _secure_session_cookie(self, response: Response):
        """Ensure session cookies are secure"""
        # This is a simplified implementation
        # In practice, you'd parse and modify Set-Cookie headers properly
        cookie_header = response.headers.get('Set-Cookie')
        if cookie_header and 'session' in cookie_header.lower():
            # Add security attributes if not present
            if 'secure' not in cookie_header.lower() and self.config.cookie_secure:
                response.headers['Set-Cookie'] += '; Secure'
            if 'httponly' not in cookie_header.lower() and self.config.cookie_httponly:
                response.headers['Set-Cookie'] += '; HttpOnly'
            if 'samesite' not in cookie_header.lower():
                response.headers['Set-Cookie'] += f'; SameSite={self.config.cookie_samesite}'


class SecurityEventLogger:
    """Log security events for monitoring and alerting"""
    
    def __init__(self, redis_client: Optional[aioredis.Redis] = None):
        self.redis_client = redis_client
        self._events: List[Dict[str, Any]] = []  # Fallback storage
    
    async def log_security_event(
        self,
        event_type: str,
        severity: str,
        description: str,
        client_ip: str,
        user_id: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ):
        """Log security event"""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "severity": severity,
            "description": description,
            "client_ip": client_ip,
            "user_id": user_id,
            "additional_data": additional_data or {}
        }
        
        # Log to structured logger
        logger.warning("Security event",
                      event_type=event_type,
                      severity=severity,
                      client_ip=client_ip,
                      user_id=user_id)
        
        # Store for analysis
        if self.redis_client:
            try:
                key = f"security_event:{datetime.utcnow().strftime('%Y%m%d')}"
                await self.redis_client.lpush(key, str(event))
                await self.redis_client.expire(key, 86400 * 30)  # Keep for 30 days
            except Exception as e:
                logger.error("Failed to store security event in Redis", error=str(e))
        else:
            self._events.append(event)
            # Keep only last 1000 events in memory
            if len(self._events) > 1000:
                self._events = self._events[-1000:]
    
    async def get_recent_events(
        self, 
        hours: int = 24, 
        event_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get recent security events"""
        try:
            if self.redis_client:
                # Get events from Redis
                events = []
                for days_back in range((hours // 24) + 1):
                    date = datetime.utcnow() - timedelta(days=days_back)
                    key = f"security_event:{date.strftime('%Y%m%d')}"
                    day_events = await self.redis_client.lrange(key, 0, -1)
                    
                    for event_str in day_events:
                        try:
                            event = eval(event_str)  # In production, use proper JSON parsing
                            event_time = datetime.fromisoformat(event["timestamp"])
                            
                            if (datetime.utcnow() - event_time).total_seconds() <= hours * 3600:
                                if not event_type or event["event_type"] == event_type:
                                    events.append(event)
                        except Exception:
                            continue
                
                return sorted(events, key=lambda x: x["timestamp"], reverse=True)
            else:
                # Use local storage
                cutoff_time = datetime.utcnow() - timedelta(hours=hours)
                return [
                    event for event in self._events
                    if datetime.fromisoformat(event["timestamp"]) >= cutoff_time
                    and (not event_type or event["event_type"] == event_type)
                ]
        
        except Exception as e:
            logger.error("Failed to get security events", error=str(e))
            return []