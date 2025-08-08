"""
BFF (Backend-for-Frontend) API Routes

Provides unified API endpoints for the React frontend through the API Gateway.
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import structlog

from ...gateway import QenergyZBFF, OAuthProvider, OAuthConfig
from ...gateway.bff import BFFRequest, BFFResponse
from ...gateway.oauth_provider import OAuthProviderHandler, OAuthError
from ...config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()
security = HTTPBearer()

# Initialize BFF and OAuth handler
bff = QenergyZBFF()
oauth_handler = OAuthProviderHandler()

# API Router
router = APIRouter(prefix="/api/v1/bff", tags=["BFF Gateway"])


class BFFApiRequest(BaseModel):
    """API request model for BFF operations"""
    service: str = Field(..., description="Target service name")
    operation: str = Field(..., description="Operation to perform") 
    data: Dict[str, Any] = Field(default_factory=dict, description="Request data")
    region: str = Field(default="global", description="Regional context")


class OAuthLoginRequest(BaseModel):
    """OAuth login initiation request"""
    provider: str = Field(..., description="OAuth provider name")
    redirect_uri: Optional[str] = Field(None, description="Custom redirect URI")


class OAuthCallbackRequest(BaseModel):
    """OAuth callback request"""
    provider: str = Field(..., description="OAuth provider name")
    code: str = Field(..., description="Authorization code")
    state: str = Field(..., description="State parameter")


async def get_current_user_from_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Extract user information from JWT token"""
    # This is a simplified implementation
    # In production, you'd validate the JWT token properly
    try:
        token = credentials.credentials
        # Decode JWT token and extract user info
        # For now, return a mock user
        return {
            "user_id": "user_123",
            "username": "test_user",
            "session_id": "session_456"
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.on_event("startup")
async def startup_bff():
    """Initialize BFF service"""
    try:
        await bff.initialize()
        logger.info("BFF service started successfully")
    except Exception as e:
        logger.error("Failed to initialize BFF service", error=str(e))


@router.on_event("shutdown")
async def shutdown_bff():
    """Shutdown BFF service"""
    try:
        await bff.shutdown()
        await oauth_handler.close()
        logger.info("BFF service shut down successfully")
    except Exception as e:
        logger.error("Failed to shutdown BFF service", error=str(e))


@router.post("/request", response_model=BFFResponse)
async def handle_bff_request(
    request_data: BFFApiRequest,
    user: Dict[str, Any] = Depends(get_current_user_from_token)
) -> BFFResponse:
    """
    Process BFF request through the API Gateway
    
    This endpoint orchestrates communication between the frontend and backend services
    with rate limiting, security, and audit logging.
    """
    try:
        # Create BFF request
        bff_request = BFFRequest(
            service=request_data.service,
            operation=request_data.operation,
            data=request_data.data,
            user_id=user["user_id"],
            session_id=user["session_id"],
            region=request_data.region
        )
        
        # Process through BFF
        response = await bff.process_request(bff_request)
        
        return response
        
    except Exception as e:
        logger.error("BFF request failed", 
                    service=request_data.service,
                    operation=request_data.operation,
                    user_id=user.get("user_id"),
                    error=str(e))
        
        return BFFResponse(
            success=False,
            error=str(e),
            request_id=f"error_{datetime.utcnow().timestamp()}"
        )


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates
    
    Handles real-time communication for trading updates, market data,
    and other live information.
    """
    # Extract user info from query parameters or headers
    # In production, you'd validate the user properly
    user_id = websocket.query_params.get("user_id", "anonymous")
    session_id = websocket.query_params.get("session_id", "unknown")
    
    try:
        await bff.handle_websocket_connection(websocket, user_id, session_id)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected", user_id=user_id)
    except Exception as e:
        logger.error("WebSocket error", user_id=user_id, error=str(e))


@router.post("/oauth/login")
async def oauth_login(request_data: OAuthLoginRequest) -> Dict[str, str]:
    """
    Initiate OAuth login flow
    
    Returns authorization URL for the specified OAuth provider.
    """
    try:
        provider = OAuthProvider(request_data.provider)
        
        result = oauth_handler.get_authorization_url(
            provider=provider,
            redirect_uri=request_data.redirect_uri
        )
        
        logger.info("OAuth login initiated", provider=provider.value)
        
        return {
            "authorization_url": result["authorization_url"],
            "state": result["state"],
            "provider": provider.value
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid provider: {request_data.provider}")
    except OAuthError as e:
        logger.error("OAuth login failed", provider=request_data.provider, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("OAuth login error", provider=request_data.provider, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/oauth/callback")
async def oauth_callback(request_data: OAuthCallbackRequest) -> Dict[str, Any]:
    """
    Handle OAuth callback
    
    Exchanges authorization code for tokens and user information.
    """
    try:
        provider = OAuthProvider(request_data.provider)
        
        # Exchange code for token
        oauth_token = await oauth_handler.handle_callback(
            provider=provider,
            code=request_data.code,
            state=request_data.state
        )
        
        # Get user information
        user_info = await oauth_handler.get_user_info(provider, oauth_token)
        
        # Here you would typically:
        # 1. Create or update user in your database
        # 2. Generate your application's JWT token
        # 3. Create user session
        
        logger.info("OAuth login successful", 
                   provider=provider.value,
                   user_id=user_info.id,
                   email=user_info.email)
        
        return {
            "success": True,
            "user": {
                "id": user_info.id,
                "email": user_info.email,
                "name": user_info.name,
                "first_name": user_info.first_name,
                "last_name": user_info.last_name,
                "picture": user_info.picture,
                "provider": provider.value
            },
            "token": {
                "access_token": oauth_token.access_token,
                "token_type": oauth_token.token_type,
                "expires_in": oauth_token.expires_in,
                # Don't return refresh_token to frontend for security
            }
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid provider: {request_data.provider}")
    except OAuthError as e:
        logger.error("OAuth callback failed", 
                    provider=request_data.provider, 
                    error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("OAuth callback error", 
                    provider=request_data.provider, 
                    error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/oauth/providers")
async def get_oauth_providers() -> Dict[str, List[str]]:
    """Get list of configured OAuth providers"""
    try:
        providers = oauth_handler.get_supported_providers()
        return {
            "providers": [provider.value for provider in providers]
        }
    except Exception as e:
        logger.error("Failed to get OAuth providers", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/health")
async def bff_health_check() -> Dict[str, Any]:
    """BFF health check endpoint"""
    try:
        # Check BFF service status
        # In production, you'd check Redis, database connectivity, etc.
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "bff": "operational",
                "oauth": "operational",
                "redis": "operational" if bff.redis_client else "not_configured",
            },
            "oauth_providers": [p.value for p in oauth_handler.get_supported_providers()]
        }
        
    except Exception as e:
        logger.error("BFF health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }