"""
Backend-for-Frontend (BFF) Service

Orchestrates communication between React frontend and backend services.
"""

import asyncio
import json
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
import structlog
from fastapi import Request, Response, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import redis.asyncio as aioredis
from contextlib import asynccontextmanager

from ..config import get_settings
from ..services.trading import TradingService
from ..services.risk import RiskService  
from ..services.compliance import ComplianceService
from ..services.iot import IoTService
from .rate_limiter import RateLimiter
from .circuit_breaker import CircuitBreaker
from .audit_logger import AuditLogger

logger = structlog.get_logger(__name__)
settings = get_settings()


class BFFRequest(BaseModel):
    """Request model for BFF operations"""
    service: str = Field(..., description="Target service (trading, risk, compliance, iot)")
    operation: str = Field(..., description="Operation to perform")
    data: Dict[str, Any] = Field(default_factory=dict, description="Request data")
    user_id: str = Field(..., description="User ID for audit logging")
    session_id: str = Field(..., description="Session ID")
    region: str = Field(default="global", description="Regional context")


class BFFResponse(BaseModel):
    """Response model for BFF operations"""
    success: bool = Field(..., description="Operation success status")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    error: Optional[str] = Field(None, description="Error message if any")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: str = Field(..., description="Unique request ID for tracing")


class WebSocketManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        self.connections: Dict[str, List[WebSocket]] = {}
        self.user_sessions: Dict[str, str] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str, session_id: str):
        """Accept and register a WebSocket connection"""
        await websocket.accept()
        if user_id not in self.connections:
            self.connections[user_id] = []
        self.connections[user_id].append(websocket)
        self.user_sessions[user_id] = session_id
        
        logger.info("WebSocket connected", user_id=user_id, session_id=session_id)
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        """Remove WebSocket connection"""
        if user_id in self.connections:
            if websocket in self.connections[user_id]:
                self.connections[user_id].remove(websocket)
                if not self.connections[user_id]:
                    del self.connections[user_id]
                    if user_id in self.user_sessions:
                        del self.user_sessions[user_id]
        
        logger.info("WebSocket disconnected", user_id=user_id)
    
    async def send_to_user(self, user_id: str, message: Dict[str, Any]):
        """Send message to all user's WebSocket connections"""
        if user_id in self.connections:
            disconnected = []
            for websocket in self.connections[user_id]:
                try:
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    logger.warning("Failed to send WebSocket message", 
                                 user_id=user_id, error=str(e))
                    disconnected.append(websocket)
            
            # Clean up disconnected websockets
            for websocket in disconnected:
                self.disconnect(websocket, user_id)
    
    async def broadcast(self, message: Dict[str, Any], user_filter: Optional[callable] = None):
        """Broadcast message to all or filtered connections"""
        for user_id in list(self.connections.keys()):
            if user_filter is None or user_filter(user_id):
                await self.send_to_user(user_id, message)


class QenergyZBFF:
    """
    Backend-for-Frontend (BFF) Service
    
    Provides a unified API gateway for the React frontend with:
    - Service orchestration
    - Rate limiting and security
    - WebSocket management for real-time updates
    - Circuit breakers for fault tolerance
    - Request/response transformation
    - Audit logging
    """
    
    def __init__(self):
        self.trading_service = TradingService()
        self.risk_service = RiskService()
        self.compliance_service = ComplianceService()
        self.iot_service = IoTService()
        
        self.rate_limiter = RateLimiter()
        self.circuit_breaker = CircuitBreaker()
        self.audit_logger = AuditLogger()
        self.websocket_manager = WebSocketManager()
        
        self.redis_client: Optional[aioredis.Redis] = None
        
    async def initialize(self):
        """Initialize BFF service with Redis connection"""
        try:
            self.redis_client = aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("BFF service initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize BFF service", error=str(e))
            raise
    
    async def shutdown(self):
        """Cleanup resources"""
        if self.redis_client:
            await self.redis_client.close()
        logger.info("BFF service shut down")
    
    @asynccontextmanager
    async def request_context(self, request_id: str, user_id: str, operation: str):
        """Context manager for request processing with audit logging"""
        start_time = datetime.utcnow()
        
        await self.audit_logger.log_request_start(
            request_id=request_id,
            user_id=user_id,
            operation=operation,
            timestamp=start_time
        )
        
        try:
            yield
        except Exception as e:
            await self.audit_logger.log_request_error(
                request_id=request_id,
                user_id=user_id,
                operation=operation,
                error=str(e),
                timestamp=datetime.utcnow()
            )
            raise
        finally:
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            await self.audit_logger.log_request_end(
                request_id=request_id,
                user_id=user_id,
                operation=operation,
                duration=duration,
                timestamp=end_time
            )
    
    async def process_request(self, request: BFFRequest) -> BFFResponse:
        """
        Process BFF request with service orchestration
        
        Args:
            request: BFF request object
            
        Returns:
            BFF response object
        """
        request_id = f"{request.user_id}_{datetime.utcnow().timestamp()}"
        
        # Rate limiting check
        if not await self.rate_limiter.check_rate_limit(request.user_id):
            raise HTTPException(
                status_code=429, 
                detail="Rate limit exceeded"
            )
        
        async with self.request_context(request_id, request.user_id, request.operation):
            try:
                # Circuit breaker check
                if not self.circuit_breaker.can_proceed(request.service):
                    raise HTTPException(
                        status_code=503,
                        detail=f"Service {request.service} temporarily unavailable"
                    )
                
                # Route request to appropriate service
                result = await self._route_request(request)
                
                # Cache successful response if configured
                if settings.enable_response_caching:
                    await self._cache_response(request_id, result)
                
                # Send real-time update via WebSocket
                await self._send_realtime_update(request, result)
                
                # Mark circuit breaker success
                self.circuit_breaker.record_success(request.service)
                
                return BFFResponse(
                    success=True,
                    data=result,
                    request_id=request_id
                )
                
            except Exception as e:
                # Mark circuit breaker failure
                self.circuit_breaker.record_failure(request.service)
                
                logger.error(
                    "BFF request processing failed",
                    request_id=request_id,
                    user_id=request.user_id,
                    service=request.service,
                    operation=request.operation,
                    error=str(e)
                )
                
                return BFFResponse(
                    success=False,
                    error=str(e),
                    request_id=request_id
                )
    
    async def _route_request(self, request: BFFRequest) -> Dict[str, Any]:
        """Route request to appropriate service"""
        if request.service == "trading":
            return await self._handle_trading_request(request)
        elif request.service == "risk":
            return await self._handle_risk_request(request)
        elif request.service == "compliance":
            return await self._handle_compliance_request(request)
        elif request.service == "iot":
            return await self._handle_iot_request(request)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown service: {request.service}"
            )
    
    async def _handle_trading_request(self, request: BFFRequest) -> Dict[str, Any]:
        """Handle trading service requests"""
        if request.operation == "create_order":
            order = await self.trading_service.create_order(
                user_id=request.user_id,
                **request.data
            )
            return {"order": order.dict()}
            
        elif request.operation == "get_portfolio":
            portfolio = await self.trading_service.get_portfolio(request.user_id)
            return {"portfolio": portfolio}
            
        elif request.operation == "get_market_data":
            market_data = await self.trading_service.get_market_data(
                request.data.get("symbols", [])
            )
            return {"market_data": market_data}
            
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown trading operation: {request.operation}"
            )
    
    async def _handle_risk_request(self, request: BFFRequest) -> Dict[str, Any]:
        """Handle risk service requests"""
        if request.operation == "calculate_var":
            var_result = await self.risk_service.calculate_value_at_risk(
                portfolio_id=request.data.get("portfolio_id"),
                confidence_level=request.data.get("confidence_level", 0.95),
                time_horizon=request.data.get("time_horizon", 1)
            )
            return {"var": var_result}
            
        elif request.operation == "stress_test":
            stress_result = await self.risk_service.perform_stress_test(
                portfolio_id=request.data.get("portfolio_id"),
                scenario=request.data.get("scenario")
            )
            return {"stress_test": stress_result}
            
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown risk operation: {request.operation}"
            )
    
    async def _handle_compliance_request(self, request: BFFRequest) -> Dict[str, Any]:
        """Handle compliance service requests"""
        if request.operation == "validate_trade":
            validation_result = await self.compliance_service.validate_trade_compliance(
                trade_data=request.data,
                region=request.region
            )
            return {"validation": validation_result}
            
        elif request.operation == "get_regulations":
            regulations = await self.compliance_service.get_applicable_regulations(
                region=request.region,
                trade_type=request.data.get("trade_type")
            )
            return {"regulations": regulations}
            
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown compliance operation: {request.operation}"
            )
    
    async def _handle_iot_request(self, request: BFFRequest) -> Dict[str, Any]:
        """Handle IoT service requests"""
        if request.operation == "get_device_data":
            device_data = await self.iot_service.get_device_data(
                device_id=request.data.get("device_id"),
                start_time=request.data.get("start_time"),
                end_time=request.data.get("end_time")
            )
            return {"device_data": device_data}
            
        elif request.operation == "send_device_command":
            command_result = await self.iot_service.send_device_command(
                device_id=request.data.get("device_id"),
                command=request.data.get("command"),
                parameters=request.data.get("parameters", {})
            )
            return {"command_result": command_result}
            
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown IoT operation: {request.operation}"
            )
    
    async def _cache_response(self, request_id: str, result: Dict[str, Any]):
        """Cache response in Redis"""
        if self.redis_client:
            try:
                cache_key = f"bff:response:{request_id}"
                await self.redis_client.setex(
                    cache_key,
                    settings.response_cache_ttl,
                    json.dumps(result, default=str)
                )
            except Exception as e:
                logger.warning("Failed to cache response", 
                             request_id=request_id, error=str(e))
    
    async def _send_realtime_update(self, request: BFFRequest, result: Dict[str, Any]):
        """Send real-time update via WebSocket"""
        try:
            message = {
                "type": "service_update",
                "service": request.service,
                "operation": request.operation,
                "data": result,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.websocket_manager.send_to_user(request.user_id, message)
            
        except Exception as e:
            logger.warning("Failed to send WebSocket update", 
                         user_id=request.user_id, error=str(e))
    
    async def handle_websocket_connection(self, websocket: WebSocket, user_id: str, session_id: str):
        """Handle WebSocket connection lifecycle"""
        await self.websocket_manager.connect(websocket, user_id, session_id)
        
        try:
            while True:
                # Listen for messages from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                elif message.get("type") == "subscribe":
                    # Handle subscription to real-time updates
                    await self._handle_subscription(websocket, user_id, message)
                    
        except WebSocketDisconnect:
            self.websocket_manager.disconnect(websocket, user_id)
        except Exception as e:
            logger.error("WebSocket error", user_id=user_id, error=str(e))
            self.websocket_manager.disconnect(websocket, user_id)
    
    async def _handle_subscription(self, websocket: WebSocket, user_id: str, message: Dict[str, Any]):
        """Handle WebSocket subscription requests"""
        subscription_type = message.get("subscription")
        
        if subscription_type == "market_data":
            # Subscribe to market data updates
            symbols = message.get("symbols", [])
            # Implementation would depend on market data provider
            await websocket.send_text(json.dumps({
                "type": "subscription_confirmed",
                "subscription": "market_data",
                "symbols": symbols
            }))
            
        elif subscription_type == "portfolio_updates":
            # Subscribe to portfolio updates
            await websocket.send_text(json.dumps({
                "type": "subscription_confirmed", 
                "subscription": "portfolio_updates"
            }))
    
    async def broadcast_market_update(self, symbol: str, price_data: Dict[str, Any]):
        """Broadcast market data update to subscribed users"""
        message = {
            "type": "market_update",
            "symbol": symbol,
            "data": price_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Filter users who are subscribed to this symbol
        def user_filter(user_id: str) -> bool:
            # This would check user's subscriptions
            # Implementation depends on subscription storage
            return True  # Simplified for now
        
        await self.websocket_manager.broadcast(message, user_filter)