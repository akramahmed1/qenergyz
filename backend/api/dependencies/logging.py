"""
Logging Dependencies

Structured logging, audit trails, and security event logging.
"""

import json
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
import hashlib

from ..dependencies.database import get_db_session
from ..models.audit_log import AuditLog, AuditAction, AuditResource
from ..utils.config import get_settings


logger = structlog.get_logger(__name__)
settings = get_settings()


class AuditLogger:
    """Comprehensive audit logging system"""
    
    @staticmethod
    async def log_user_action(
        user_id: str,
        action: AuditAction,
        resource: AuditResource,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None
    ):
        """Log user action for audit trail"""
        db = await get_db_session()
        
        try:
            audit_entry = AuditLog(
                user_id=user_id,
                action=action,
                resource=resource,
                resource_id=resource_id,
                details=details or {},
                ip_address=request.client.host if request and request.client else "unknown",
                user_agent=request.headers.get("user-agent", "unknown") if request else "unknown",
                timestamp=datetime.utcnow()
            )
            
            db.add(audit_entry)
            await db.commit()
            
            # Also log to structured logger
            logger.info(
                "User action logged",
                user_id=user_id,
                action=action.value,
                resource=resource.value,
                resource_id=resource_id,
                details=details
            )
            
        except Exception as e:
            logger.error("Failed to log audit entry", error=str(e))
            await db.rollback()
        finally:
            await db.close()
    
    @staticmethod
    async def log_security_event(
        event_type: str,
        severity: str,
        description: str,
        user_id: Optional[str] = None,
        request: Optional[Request] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ):
        """Log security-related events"""
        event_data = {
            "event_type": event_type,
            "severity": severity,
            "description": description,
            "user_id": user_id,
            "ip_address": request.client.host if request and request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown") if request else "unknown",
            "timestamp": datetime.utcnow().isoformat(),
            "additional_data": additional_data or {}
        }
        
        logger.warning(
            "Security event",
            **event_data
        )
        
        # For high-severity events, also store in database
        if severity in ["high", "critical"]:
            await AuditLogger.log_user_action(
                user_id=user_id or "system",
                action=AuditAction.SECURITY_EVENT,
                resource=AuditResource.SYSTEM,
                details=event_data,
                request=request
            )
    
    @staticmethod
    async def log_api_access(
        request: Request,
        response: Response,
        user_id: Optional[str] = None,
        processing_time: Optional[float] = None
    ):
        """Log API access for monitoring"""
        # Sanitize sensitive data from URLs
        path = request.url.path
        query_params = dict(request.query_params)
        
        # Remove sensitive parameters
        sensitive_params = ["password", "token", "secret", "key", "auth"]
        for param in list(query_params.keys()):
            if any(sensitive in param.lower() for sensitive in sensitive_params):
                query_params[param] = "[REDACTED]"
        
        access_data = {
            "method": request.method,
            "path": path,
            "query_params": query_params,
            "status_code": response.status_code,
            "user_id": user_id,
            "ip_address": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown"),
            "processing_time_ms": round(processing_time * 1000, 2) if processing_time else None,
            "content_length": response.headers.get("content-length"),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Log with appropriate level based on status code
        if response.status_code >= 500:
            logger.error("API access - server error", **access_data)
        elif response.status_code >= 400:
            logger.warning("API access - client error", **access_data)
        else:
            logger.info("API access", **access_data)


class RequestLogger:
    """Request/response logging middleware"""
    
    def __init__(self):
        self.audit_logger = AuditLogger()
    
    async def log_request(
        self,
        request: Request,
        response: Response,
        processing_time: float,
        user_id: Optional[str] = None
    ):
        """Log request details"""
        await self.audit_logger.log_api_access(
            request=request,
            response=response,
            user_id=user_id,
            processing_time=processing_time
        )
    
    @staticmethod
    def get_request_id(request: Request) -> str:
        """Generate unique request ID"""
        request_data = f"{request.method}:{request.url}:{time.time()}"
        return hashlib.md5(request_data.encode()).hexdigest()[:16]


class ComplianceLogger:
    """Compliance-specific logging"""
    
    @staticmethod
    async def log_trade_activity(
        user_id: str,
        trade_id: str,
        action: str,
        instrument: str,
        quantity: float,
        price: float,
        region: str,
        request: Optional[Request] = None
    ):
        """Log trading activity for compliance"""
        await AuditLogger.log_user_action(
            user_id=user_id,
            action=AuditAction.TRADE,
            resource=AuditResource.TRADE,
            resource_id=trade_id,
            details={
                "action": action,
                "instrument": instrument,
                "quantity": quantity,
                "price": price,
                "region": region,
                "timestamp": datetime.utcnow().isoformat()
            },
            request=request
        )
        
        logger.info(
            "Trade activity logged",
            user_id=user_id,
            trade_id=trade_id,
            action=action,
            instrument=instrument,
            quantity=quantity,
            price=price,
            region=region
        )
    
    @staticmethod
    async def log_compliance_check(
        user_id: str,
        check_type: str,
        result: str,
        details: Dict[str, Any],
        request: Optional[Request] = None
    ):
        """Log compliance checks"""
        await AuditLogger.log_user_action(
            user_id=user_id,
            action=AuditAction.COMPLIANCE_CHECK,
            resource=AuditResource.COMPLIANCE,
            details={
                "check_type": check_type,
                "result": result,
                "details": details,
                "timestamp": datetime.utcnow().isoformat()
            },
            request=request
        )
        
        logger.info(
            "Compliance check logged",
            user_id=user_id,
            check_type=check_type,
            result=result
        )
    
    @staticmethod
    async def log_risk_event(
        user_id: str,
        event_type: str,
        risk_level: str,
        description: str,
        metrics: Dict[str, Any],
        request: Optional[Request] = None
    ):
        """Log risk management events"""
        await AuditLogger.log_user_action(
            user_id=user_id,
            action=AuditAction.RISK_EVENT,
            resource=AuditResource.RISK,
            details={
                "event_type": event_type,
                "risk_level": risk_level,
                "description": description,
                "metrics": metrics,
                "timestamp": datetime.utcnow().isoformat()
            },
            request=request
        )
        
        logger.warning(
            "Risk event logged",
            user_id=user_id,
            event_type=event_type,
            risk_level=risk_level,
            description=description,
            metrics=metrics
        )


class DataPrivacyLogger:
    """Data privacy and GDPR compliance logging"""
    
    @staticmethod
    async def log_data_access(
        user_id: str,
        accessed_user_id: str,
        data_type: str,
        purpose: str,
        request: Optional[Request] = None
    ):
        """Log personal data access for GDPR compliance"""
        await AuditLogger.log_user_action(
            user_id=user_id,
            action=AuditAction.DATA_ACCESS,
            resource=AuditResource.USER_DATA,
            resource_id=accessed_user_id,
            details={
                "data_type": data_type,
                "purpose": purpose,
                "timestamp": datetime.utcnow().isoformat()
            },
            request=request
        )
    
    @staticmethod
    async def log_data_export(
        user_id: str,
        exported_user_id: str,
        data_types: List[str],
        format: str,
        request: Optional[Request] = None
    ):
        """Log data export requests (GDPR Right to Portability)"""
        await AuditLogger.log_user_action(
            user_id=user_id,
            action=AuditAction.DATA_EXPORT,
            resource=AuditResource.USER_DATA,
            resource_id=exported_user_id,
            details={
                "data_types": data_types,
                "format": format,
                "timestamp": datetime.utcnow().isoformat()
            },
            request=request
        )
    
    @staticmethod
    async def log_data_deletion(
        user_id: str,
        deleted_user_id: str,
        data_types: List[str],
        reason: str,
        request: Optional[Request] = None
    ):
        """Log data deletion requests (GDPR Right to Erasure)"""
        await AuditLogger.log_user_action(
            user_id=user_id,
            action=AuditAction.DATA_DELETION,
            resource=AuditResource.USER_DATA,
            resource_id=deleted_user_id,
            details={
                "data_types": data_types,
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat()
            },
            request=request
        )


# Global logger instances
audit_logger = AuditLogger()
request_logger = RequestLogger()
compliance_logger = ComplianceLogger()
privacy_logger = DataPrivacyLogger()