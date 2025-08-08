"""
Middleware Configuration

Security and request processing middleware.
"""

import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
import structlog

from .config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


def setup_middleware(app: FastAPI):
    """Setup application middleware"""
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_credentials,
        allow_methods=settings.cors_methods,
        allow_headers=settings.cors_headers,
    )
    
    # Trusted host middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts
    )
    
    # HTTPS redirect for production
    if settings.environment == "production":
        app.add_middleware(HTTPSRedirectMiddleware)
    
    # Custom request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log HTTP requests"""
        start_time = time.time()
        
        # Get user info if available
        user_id = None
        try:
            auth_header = request.headers.get("authorization", "")
            if auth_header.startswith("Bearer "):
                from ..dependencies.auth import JWTHandler
                token = auth_header.split(" ")[1]
                token_data = JWTHandler.verify_token(token)
                user_id = token_data.user_id
        except:
            pass
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        
        logger.info(
            "HTTP request",
            method=request.method,
            url=str(request.url),
            status_code=response.status_code,
            process_time=round(process_time * 1000, 2),
            user_id=user_id,
            user_agent=request.headers.get("user-agent", "unknown"),
            client_ip=request.client.host if request.client else "unknown"
        )
        
        return response