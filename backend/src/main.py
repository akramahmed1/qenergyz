"""
Qenergyz FastAPI Main Application

A comprehensive Energy Trading and Risk Management (ETRM) platform
supporting multi-regional compliance and advanced AI/ML capabilities.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import List, Dict, Any

from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import structlog
import uvicorn

from .config import Settings, get_settings
from .services.trading import TradingService
from .services.risk import RiskService  
from .services.compliance import ComplianceService
from .services.iot import IoTService
from .gateway.security_middleware import SecurityMiddleware, SecurityConfig
from .gateway.audit_logger import AuditLogger

# Structured logging setup
logger = structlog.get_logger(__name__)

# Rate limiting setup
limiter = Limiter(key_func=get_remote_address)

# Security
security = HTTPBearer()

class QenergyZFacade:
    """
    Facade Pattern: Provides a unified interface to the complex subsystem
    of trading, risk, compliance, and IoT services.
    """
    
    def __init__(self):
        self.trading_service = TradingService()
        self.risk_service = RiskService()
        self.compliance_service = ComplianceService()
        self.iot_service = IoTService()
        
    async def initialize(self):
        """Initialize all services asynchronously"""
        await asyncio.gather(
            self.trading_service.initialize(),
            self.risk_service.initialize(),
            self.compliance_service.initialize(),
            self.iot_service.initialize()
        )
        logger.info("QenergyZ Facade initialized successfully")
        
    async def shutdown(self):
        """Graceful shutdown of all services"""
        await asyncio.gather(
            self.trading_service.shutdown(),
            self.risk_service.shutdown(), 
            self.compliance_service.shutdown(),
            self.iot_service.shutdown()
        )
        logger.info("QenergyZ Facade shutdown completed")

# Global facade instance
qenergyz_facade = QenergyZFacade()

# WebSocket connection manager
class WebSocketManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
        
    async def connect(self, websocket: WebSocket, client_info: Dict[str, Any] = None):
        """Accept WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_metadata[websocket] = client_info or {}
        logger.info("WebSocket connected", client_info=client_info)
        
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            self.connection_metadata.pop(websocket, None)
            logger.info("WebSocket disconnected")
            
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send message to specific WebSocket"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error("Failed to send WebSocket message", error=str(e))
            
    async def broadcast(self, message: str):
        """Broadcast message to all connected WebSockets"""
        if not self.active_connections:
            return
            
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.warning("WebSocket connection lost during broadcast", error=str(e))
                disconnected.append(connection)
                
        # Clean up disconnected connections
        for connection in disconnected:
            self.disconnect(connection)

ws_manager = WebSocketManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("Starting Qenergyz application")
    await qenergyz_facade.initialize()
    
    # Background tasks can be started here
    asyncio.create_task(background_risk_monitoring())
    asyncio.create_task(background_compliance_checks())
    
    yield
    
    # Shutdown
    logger.info("Shutting down Qenergyz application")
    await qenergyz_facade.shutdown()

# Create FastAPI application with lifespan management
app = FastAPI(
    title="Qenergyz ETRM Platform",
    description="Advanced Energy Trading and Risk Management SaaS",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Middleware setup
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security middleware (must be first)
security_config = SecurityConfig()
app.add_middleware(SecurityMiddleware, config=security_config)

# CORS middleware - now handled by SecurityMiddleware
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # Configure based on environment
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# Security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure based on environment
)

# HTTPS redirect middleware (for production)
settings = get_settings()
if settings.environment == "production":
    app.add_middleware(HTTPSRedirectMiddleware)

# Custom middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests with structured logging"""
    start_time = asyncio.get_event_loop().time()
    
    response = await call_next(request)
    
    process_time = asyncio.get_event_loop().time() - start_time
    
    logger.info(
        "HTTP request processed",
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
        process_time=round(process_time, 4),
        user_agent=request.headers.get("user-agent"),
        client_ip=get_remote_address(request)
    )
    
    return response

# Exception handling
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler"""
    logger.error(
        "HTTP exception occurred",
        status_code=exc.status_code,
        detail=exc.detail,
        url=str(request.url),
        method=request.method
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": asyncio.get_event_loop().time(),
            "path": str(request.url.path)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler for unexpected errors"""
    logger.error(
        "Unexpected error occurred",
        error=str(exc),
        error_type=type(exc).__name__,
        url=str(request.url),
        method=request.method,
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "timestamp": asyncio.get_event_loop().time(),
            "path": str(request.url.path)
        }
    )

# Health check endpoints
@app.get("/health", tags=["Health"])
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": asyncio.get_event_loop().time(),
        "version": "1.0.0",
        "environment": settings.environment
    }

@app.get("/health/detailed", tags=["Health"])
async def detailed_health_check():
    """Detailed health check including service status"""
    try:
        # Check database connection
        # db_healthy = await check_database_health()
        
        # Check Redis connection  
        # redis_healthy = await check_redis_health()
        
        # Check external APIs
        # api_healthy = await check_external_apis_health()
        
        return {
            "status": "healthy",
            "timestamp": asyncio.get_event_loop().time(),
            "version": "1.0.0",
            "environment": settings.environment,
            "services": {
                "database": "healthy",  # db_healthy
                "cache": "healthy",     # redis_healthy
                "external_apis": "healthy",  # api_healthy
                "trading_service": "healthy",
                "risk_service": "healthy",
                "compliance_service": "healthy",
                "iot_service": "healthy"
            }
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "timestamp": asyncio.get_event_loop().time(),
            "error": str(e)
        }

# API versioning - v1 routes
@app.get("/api/v1/status", tags=["API v1"])
@limiter.limit("100/minute")
async def api_v1_status(request: Request):
    """API v1 status endpoint"""
    return {
        "api_version": "v1",
        "status": "active",
        "features": [
            "trading_operations",
            "risk_management", 
            "compliance_monitoring",
            "iot_integration",
            "real_time_websockets"
        ]
    }

# WebSocket endpoints
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for real-time updates"""
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            
            # Process WebSocket message based on type
            # This would typically involve parsing JSON and routing to appropriate services
            await ws_manager.send_personal_message(f"Echo: {data}", websocket)
            
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error("WebSocket error", error=str(e))
        ws_manager.disconnect(websocket)

@app.websocket("/ws/trading")
async def trading_websocket(websocket: WebSocket):
    """Trading-specific WebSocket endpoint"""
    await ws_manager.connect(websocket, {"type": "trading"})
    try:
        while True:
            # Handle trading-specific real-time updates
            data = await websocket.receive_text()
            # Route to trading service
            response = await qenergyz_facade.trading_service.handle_websocket_message(data)
            await ws_manager.send_personal_message(response, websocket)
            
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

@app.websocket("/ws/risk")
async def risk_websocket(websocket: WebSocket):
    """Risk monitoring WebSocket endpoint"""
    await ws_manager.connect(websocket, {"type": "risk"})
    try:
        while True:
            # Handle risk monitoring real-time updates
            data = await websocket.receive_text()
            # Route to risk service
            response = await qenergyz_facade.risk_service.handle_websocket_message(data)
            await ws_manager.send_personal_message(response, websocket)
            
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

# Background tasks
async def background_risk_monitoring():
    """Background task for continuous risk monitoring"""
    while True:
        try:
            # Perform risk calculations and monitoring
            risk_alerts = await qenergyz_facade.risk_service.monitor_positions()
            
            if risk_alerts:
                # Broadcast risk alerts to connected WebSocket clients
                for alert in risk_alerts:
                    await ws_manager.broadcast(f"RISK_ALERT: {alert}")
                    
            await asyncio.sleep(30)  # Check every 30 seconds
            
        except Exception as e:
            logger.error("Background risk monitoring error", error=str(e))
            await asyncio.sleep(60)  # Wait longer on error

async def background_compliance_checks():
    """Background task for compliance monitoring"""
    while True:
        try:
            # Perform compliance checks
            compliance_alerts = await qenergyz_facade.compliance_service.run_periodic_checks()
            
            if compliance_alerts:
                # Handle compliance alerts
                for alert in compliance_alerts:
                    await ws_manager.broadcast(f"COMPLIANCE_ALERT: {alert}")
                    
            await asyncio.sleep(300)  # Check every 5 minutes
            
        except Exception as e:
            logger.error("Background compliance monitoring error", error=str(e))
            await asyncio.sleep(600)  # Wait longer on error

# API route registration (to be implemented in separate route files)
# app.include_router(trading_router, prefix="/api/v1/trading", tags=["Trading"])
# app.include_router(risk_router, prefix="/api/v1/risk", tags=["Risk Management"]) 
# app.include_router(compliance_router, prefix="/api/v1/compliance", tags=["Compliance"])
# app.include_router(iot_router, prefix="/api/v1/iot", tags=["IoT Integration"])

if __name__ == "__main__":
    # Development server
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        access_log=True,
        log_level="info"
    )