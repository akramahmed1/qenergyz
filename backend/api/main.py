"""
Qenergyz Main API Application

FastAPI application entry point with authentication, database,
and comprehensive security features.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import structlog

from .dependencies.auth import get_current_user
from .dependencies.database import get_db
from .dependencies.rate_limiting import limiter
from .routes import auth, users, trading, onboarding, compliance, risk
from .utils.exceptions import setup_exception_handlers
from .utils.middleware import setup_middleware
from .utils.logging import setup_logging
from .models.database import init_database, close_database


# Setup structured logging
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("Starting Qenergyz API application")
    
    # Initialize database
    await init_database()
    
    # Setup logging
    setup_logging()
    
    logger.info("Qenergyz API application started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Qenergyz API application")
    
    # Close database connections
    await close_database()
    
    logger.info("Qenergyz API application shutdown completed")


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    
    app = FastAPI(
        title="Qenergyz ETRM API",
        description="Advanced Energy Trading and Risk Management API with comprehensive authentication and security",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan
    )
    
    # Setup middleware
    setup_middleware(app)
    
    # Setup exception handlers
    setup_exception_handlers(app)
    
    # Add rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    # Include routers
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
    app.include_router(users.router, prefix="/api/v1/users", tags=["User Management"])
    app.include_router(trading.router, prefix="/api/v1/trading", tags=["Trading"])
    app.include_router(onboarding.router, prefix="/api/v1/onboarding", tags=["Onboarding"])
    app.include_router(compliance.router, prefix="/api/v1/compliance", tags=["Compliance"])
    app.include_router(risk.router, prefix="/api/v1/risk", tags=["Risk Management"])
    
    # Health check endpoints
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Basic health check endpoint"""
        return {
            "status": "healthy",
            "version": "1.0.0",
            "environment": "development"
        }
    
    @app.get("/api/v1/status", tags=["API Status"])
    @limiter.limit("100/minute")
    async def api_status(request: Request):
        """API status endpoint with rate limiting"""
        return {
            "api_version": "v1",
            "status": "active",
            "features": [
                "authentication",
                "user_management",
                "trading_operations",
                "onboarding",
                "compliance_monitoring",
                "risk_management"
            ]
        }
    
    return app


# Create the app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        access_log=True,
        log_level="info"
    )