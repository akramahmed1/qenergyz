"""
Comprehensive Audit Logger for Security and Compliance

Provides detailed audit logging for:
- User actions and authentication
- API access and data changes  
- Security events and alerts
- Compliance violations
- System operations
"""

import asyncio
import json
import hashlib
import secrets
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from enum import Enum
import structlog
import redis.asyncio as aioredis
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, insert

from ..config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class AuditEventType(str, Enum):
    """Types of audit events"""
    # Authentication & Authorization
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    PASSWORD_CHANGED = "password_changed"
    MFA_ENABLED = "mfa_enabled"
    MFA_DISABLED = "mfa_disabled"
    OAUTH_LOGIN = "oauth_login"
    SESSION_EXPIRED = "session_expired"
    
    # API Access
    API_REQUEST = "api_request"
    API_ERROR = "api_error" 
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    
    # Trading Operations
    ORDER_CREATED = "order_created"
    ORDER_MODIFIED = "order_modified"
    ORDER_CANCELLED = "order_cancelled"
    TRADE_EXECUTED = "trade_executed"
    PORTFOLIO_VIEWED = "portfolio_viewed"
    
    # Risk Management
    RISK_CALCULATION = "risk_calculation"
    RISK_LIMIT_EXCEEDED = "risk_limit_exceeded"
    STRESS_TEST = "stress_test"
    
    # Compliance
    COMPLIANCE_CHECK = "compliance_check"
    COMPLIANCE_VIOLATION = "compliance_violation"
    AML_SCREENING = "aml_screening"
    REGULATORY_REPORT = "regulatory_report"
    
    # Data Access
    DATA_ACCESSED = "data_accessed"
    DATA_MODIFIED = "data_modified"
    DATA_EXPORTED = "data_exported"
    DATA_DELETED = "data_deleted"
    
    # Security Events
    SECURITY_ALERT = "security_alert"
    INTRUSION_ATTEMPT = "intrusion_attempt"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    
    # System Operations
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_SHUTDOWN = "system_shutdown"
    CONFIG_CHANGED = "config_changed"
    BACKUP_CREATED = "backup_created"


class AuditSeverity(str, Enum):
    """Audit event severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditOutcome(str, Enum):
    """Audit event outcomes"""
    SUCCESS = "success"
    FAILURE = "failure"
    WARNING = "warning"
    ERROR = "error"


class AuditEvent(BaseModel):
    """Audit event model"""
    id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: AuditEventType
    severity: AuditSeverity = AuditSeverity.MEDIUM
    outcome: AuditOutcome = AuditOutcome.SUCCESS
    
    # User and Session
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    username: Optional[str] = None
    user_role: Optional[str] = None
    
    # Request Context
    request_id: Optional[str] = None
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    method: Optional[str] = None
    endpoint: Optional[str] = None
    
    # Resource Information
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    resource_name: Optional[str] = None
    
    # Event Details
    description: str
    details: Dict[str, Any] = Field(default_factory=dict)
    
    # Changes (for data modification events)
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    
    # Geographic and Compliance
    region: Optional[str] = None
    jurisdiction: Optional[str] = None
    regulatory_context: Optional[Dict[str, str]] = None
    
    # Risk and Impact
    risk_score: Optional[float] = None
    impact_level: Optional[str] = None
    
    # Correlation
    correlation_id: Optional[str] = None
    parent_event_id: Optional[str] = None
    
    def generate_event_hash(self) -> str:
        """Generate hash for event integrity"""
        hash_data = f"{self.timestamp}{self.event_type}{self.user_id}{self.description}"
        return hashlib.sha256(hash_data.encode()).hexdigest()


class AuditFilter(BaseModel):
    """Audit log filter criteria"""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    event_types: Optional[List[AuditEventType]] = None
    user_ids: Optional[List[str]] = None
    severities: Optional[List[AuditSeverity]] = None
    outcomes: Optional[List[AuditOutcome]] = None
    client_ips: Optional[List[str]] = None
    resource_types: Optional[List[str]] = None
    correlation_id: Optional[str] = None
    search_text: Optional[str] = None
    limit: int = Field(default=100, le=1000)
    offset: int = Field(default=0, ge=0)


class ComplianceReportConfig(BaseModel):
    """Configuration for compliance reports"""
    report_type: str
    jurisdiction: str
    start_date: datetime
    end_date: datetime
    include_event_types: List[AuditEventType]
    format: str = "json"  # json, csv, xml


class AuditLogger:
    """
    Comprehensive audit logging system
    
    Provides secure, tamper-evident audit logging with:
    - Multiple storage backends (Redis, Database)
    - Real-time alerting for critical events
    - Compliance reporting
    - Event correlation and analysis
    """
    
    def __init__(
        self, 
        redis_client: Optional[aioredis.Redis] = None,
        db_session: Optional[AsyncSession] = None
    ):
        self.redis_client = redis_client
        self.db_session = db_session
        self._local_buffer: List[AuditEvent] = []
        self._buffer_size = 100
        
        # Event correlation tracking
        self._correlations: Dict[str, List[str]] = {}
        
        # Real-time alerting configurations
        self.critical_event_types = {
            AuditEventType.INTRUSION_ATTEMPT,
            AuditEventType.PRIVILEGE_ESCALATION,
            AuditEventType.COMPLIANCE_VIOLATION,
            AuditEventType.RISK_LIMIT_EXCEEDED,
            AuditEventType.SECURITY_ALERT
        }
    
    async def initialize(self, redis_client: Optional[aioredis.Redis] = None, 
                        db_session: Optional[AsyncSession] = None):
        """Initialize audit logger with storage backends"""
        if redis_client:
            self.redis_client = redis_client
        if db_session:
            self.db_session = db_session
        
        logger.info("Audit logger initialized")
    
    async def log_event(
        self, 
        event_type: AuditEventType,
        description: str,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Log audit event
        
        Args:
            event_type: Type of event
            description: Event description
            user_id: User ID if applicable
            request_id: Request ID for correlation
            **kwargs: Additional event data
            
        Returns:
            Event ID
        """
        
        # Create audit event
        event = AuditEvent(
            event_type=event_type,
            description=description,
            user_id=user_id,
            request_id=request_id,
            **kwargs
        )
        
        # Generate unique event ID
        event.id = f"{event_type.value}_{datetime.utcnow().timestamp()}_{secrets.token_hex(8)}"
        
        # Add event hash for integrity
        event_hash = event.generate_event_hash()
        event.details["event_hash"] = event_hash
        
        # Store event
        await self._store_event(event)
        
        # Check for real-time alerting
        if event.event_type in self.critical_event_types or event.severity == AuditSeverity.CRITICAL:
            await self._send_critical_alert(event)
        
        # Update correlations
        if event.correlation_id:
            await self._update_correlation(event.correlation_id, event.id)
        
        logger.debug("Audit event logged", 
                    event_id=event.id, 
                    event_type=event_type,
                    user_id=user_id)
        
        return event.id
    
    async def _store_event(self, event: AuditEvent):
        """Store event in configured backends"""
        
        # Store in Redis for fast access
        if self.redis_client:
            await self._store_in_redis(event)
        
        # Store in database for long-term retention
        if self.db_session:
            await self._store_in_database(event)
        
        # Buffer locally as fallback
        self._local_buffer.append(event)
        if len(self._local_buffer) > self._buffer_size:
            self._local_buffer = self._local_buffer[-self._buffer_size:]
    
    async def _store_in_redis(self, event: AuditEvent):
        """Store event in Redis"""
        try:
            # Store event details
            event_key = f"audit:event:{event.id}"
            await self.redis_client.hset(
                event_key,
                mapping={
                    "event_data": event.json(),
                    "timestamp": event.timestamp.isoformat(),
                    "event_type": event.event_type.value,
                    "user_id": event.user_id or "",
                    "severity": event.severity.value
                }
            )
            await self.redis_client.expire(event_key, 86400 * 90)  # 90 days retention
            
            # Add to time-series index
            date_key = f"audit:by_date:{event.timestamp.strftime('%Y%m%d')}"
            await self.redis_client.zadd(
                date_key, 
                {event.id: event.timestamp.timestamp()}
            )
            await self.redis_client.expire(date_key, 86400 * 90)
            
            # Add to user index if applicable
            if event.user_id:
                user_key = f"audit:by_user:{event.user_id}"
                await self.redis_client.zadd(
                    user_key,
                    {event.id: event.timestamp.timestamp()}
                )
                await self.redis_client.expire(user_key, 86400 * 90)
            
            # Add to event type index
            type_key = f"audit:by_type:{event.event_type.value}"
            await self.redis_client.zadd(
                type_key,
                {event.id: event.timestamp.timestamp()}
            )
            await self.redis_client.expire(type_key, 86400 * 90)
            
        except Exception as e:
            logger.error("Failed to store audit event in Redis", 
                        event_id=event.id, error=str(e))
    
    async def _store_in_database(self, event: AuditEvent):
        """Store event in database"""
        try:
            # In a real implementation, you'd have a proper audit_logs table
            # This is a simplified example
            
            insert_stmt = text("""
                INSERT INTO audit_logs (
                    id, timestamp, event_type, severity, outcome,
                    user_id, session_id, request_id, client_ip,
                    description, details, region, event_hash
                ) VALUES (
                    :id, :timestamp, :event_type, :severity, :outcome,
                    :user_id, :session_id, :request_id, :client_ip,
                    :description, :details, :region, :event_hash
                )
            """)
            
            await self.db_session.execute(insert_stmt, {
                "id": event.id,
                "timestamp": event.timestamp,
                "event_type": event.event_type.value,
                "severity": event.severity.value,
                "outcome": event.outcome.value,
                "user_id": event.user_id,
                "session_id": event.session_id,
                "request_id": event.request_id,
                "client_ip": event.client_ip,
                "description": event.description,
                "details": json.dumps(event.details),
                "region": event.region,
                "event_hash": event.details.get("event_hash")
            })
            
            await self.db_session.commit()
            
        except Exception as e:
            logger.error("Failed to store audit event in database",
                        event_id=event.id, error=str(e))
            if self.db_session:
                await self.db_session.rollback()
    
    async def _send_critical_alert(self, event: AuditEvent):
        """Send real-time alert for critical events"""
        try:
            alert_data = {
                "timestamp": event.timestamp.isoformat(),
                "event_id": event.id,
                "event_type": event.event_type.value,
                "severity": event.severity.value,
                "description": event.description,
                "user_id": event.user_id,
                "client_ip": event.client_ip,
                "details": event.details
            }
            
            # Send to alerting system (Slack, email, webhook, etc.)
            if self.redis_client:
                await self.redis_client.lpush(
                    "security:critical_alerts",
                    json.dumps(alert_data)
                )
                await self.redis_client.expire("security:critical_alerts", 86400 * 7)
            
            # Log critical event
            logger.critical("Critical audit event", **alert_data)
            
        except Exception as e:
            logger.error("Failed to send critical alert", 
                        event_id=event.id, error=str(e))
    
    async def _update_correlation(self, correlation_id: str, event_id: str):
        """Update event correlation tracking"""
        try:
            if self.redis_client:
                corr_key = f"audit:correlation:{correlation_id}"
                await self.redis_client.sadd(corr_key, event_id)
                await self.redis_client.expire(corr_key, 86400 * 30)
            
            # Local correlation tracking
            if correlation_id not in self._correlations:
                self._correlations[correlation_id] = []
            self._correlations[correlation_id].append(event_id)
            
        except Exception as e:
            logger.error("Failed to update event correlation", 
                        correlation_id=correlation_id, error=str(e))
    
    async def search_events(self, filters: AuditFilter) -> List[AuditEvent]:
        """Search audit events with filters"""
        try:
            events = []
            
            if self.redis_client:
                events = await self._search_redis_events(filters)
            elif self.db_session:
                events = await self._search_database_events(filters)
            else:
                # Fallback to local buffer
                events = await self._search_local_events(filters)
            
            return events
            
        except Exception as e:
            logger.error("Failed to search audit events", error=str(e))
            return []
    
    async def _search_redis_events(self, filters: AuditFilter) -> List[AuditEvent]:
        """Search events in Redis"""
        event_ids = set()
        
        # Time-based search
        if filters.start_time or filters.end_time:
            start_ts = filters.start_time.timestamp() if filters.start_time else 0
            end_ts = filters.end_time.timestamp() if filters.end_time else float('inf')
            
            # Search by date ranges
            start_date = (filters.start_time or datetime.utcnow() - timedelta(days=30)).date()
            end_date = (filters.end_time or datetime.utcnow()).date()
            
            current_date = start_date
            while current_date <= end_date:
                date_key = f"audit:by_date:{current_date.strftime('%Y%m%d')}"
                day_event_ids = await self.redis_client.zrangebyscore(
                    date_key, start_ts, end_ts
                )
                event_ids.update(day_event_ids)
                current_date += timedelta(days=1)
        
        # Filter by user
        if filters.user_ids:
            user_event_ids = set()
            for user_id in filters.user_ids:
                user_key = f"audit:by_user:{user_id}"
                user_events = await self.redis_client.zrange(user_key, 0, -1)
                user_event_ids.update(user_events)
            
            if event_ids:
                event_ids = event_ids.intersection(user_event_ids)
            else:
                event_ids = user_event_ids
        
        # Filter by event type
        if filters.event_types:
            type_event_ids = set()
            for event_type in filters.event_types:
                type_key = f"audit:by_type:{event_type.value}"
                type_events = await self.redis_client.zrange(type_key, 0, -1)
                type_event_ids.update(type_events)
            
            if event_ids:
                event_ids = event_ids.intersection(type_event_ids)
            else:
                event_ids = type_event_ids
        
        # Get event details
        events = []
        for event_id in list(event_ids)[filters.offset:filters.offset + filters.limit]:
            event_key = f"audit:event:{event_id}"
            event_data = await self.redis_client.hget(event_key, "event_data")
            if event_data:
                try:
                    event = AuditEvent.parse_raw(event_data)
                    
                    # Apply additional filters
                    if self._matches_filters(event, filters):
                        events.append(event)
                except Exception as e:
                    logger.warning("Failed to parse audit event", 
                                  event_id=event_id, error=str(e))
        
        return sorted(events, key=lambda x: x.timestamp, reverse=True)
    
    async def _search_database_events(self, filters: AuditFilter) -> List[AuditEvent]:
        """Search events in database"""
        # Simplified database search example
        query = "SELECT * FROM audit_logs WHERE 1=1"
        params = {}
        
        if filters.start_time:
            query += " AND timestamp >= :start_time"
            params["start_time"] = filters.start_time
        
        if filters.end_time:
            query += " AND timestamp <= :end_time"
            params["end_time"] = filters.end_time
        
        if filters.user_ids:
            query += " AND user_id IN :user_ids"
            params["user_ids"] = tuple(filters.user_ids)
        
        if filters.event_types:
            query += " AND event_type IN :event_types"
            params["event_types"] = tuple([et.value for et in filters.event_types])
        
        query += " ORDER BY timestamp DESC LIMIT :limit OFFSET :offset"
        params["limit"] = filters.limit
        params["offset"] = filters.offset
        
        result = await self.db_session.execute(text(query), params)
        rows = result.fetchall()
        
        events = []
        for row in rows:
            try:
                event = AuditEvent(
                    id=row.id,
                    timestamp=row.timestamp,
                    event_type=AuditEventType(row.event_type),
                    severity=AuditSeverity(row.severity),
                    outcome=AuditOutcome(row.outcome),
                    user_id=row.user_id,
                    session_id=row.session_id,
                    request_id=row.request_id,
                    client_ip=row.client_ip,
                    description=row.description,
                    details=json.loads(row.details or "{}"),
                    region=row.region
                )
                events.append(event)
            except Exception as e:
                logger.warning("Failed to parse database audit event", error=str(e))
        
        return events
    
    async def _search_local_events(self, filters: AuditFilter) -> List[AuditEvent]:
        """Search events in local buffer"""
        events = []
        
        for event in self._local_buffer:
            if self._matches_filters(event, filters):
                events.append(event)
        
        # Sort by timestamp (newest first)
        events.sort(key=lambda x: x.timestamp, reverse=True)
        
        # Apply pagination
        return events[filters.offset:filters.offset + filters.limit]
    
    def _matches_filters(self, event: AuditEvent, filters: AuditFilter) -> bool:
        """Check if event matches filter criteria"""
        
        if filters.start_time and event.timestamp < filters.start_time:
            return False
        
        if filters.end_time and event.timestamp > filters.end_time:
            return False
        
        if filters.event_types and event.event_type not in filters.event_types:
            return False
        
        if filters.user_ids and event.user_id not in filters.user_ids:
            return False
        
        if filters.severities and event.severity not in filters.severities:
            return False
        
        if filters.outcomes and event.outcome not in filters.outcomes:
            return False
        
        if filters.client_ips and event.client_ip not in filters.client_ips:
            return False
        
        if filters.resource_types and event.resource_type not in filters.resource_types:
            return False
        
        if filters.correlation_id and event.correlation_id != filters.correlation_id:
            return False
        
        if filters.search_text:
            search_text = filters.search_text.lower()
            if (search_text not in event.description.lower() and
                search_text not in str(event.details).lower()):
                return False
        
        return True
    
    async def get_event_correlation(self, correlation_id: str) -> List[AuditEvent]:
        """Get all events for a correlation ID"""
        try:
            event_ids = []
            
            if self.redis_client:
                corr_key = f"audit:correlation:{correlation_id}"
                event_ids = await self.redis_client.smembers(corr_key)
            elif correlation_id in self._correlations:
                event_ids = self._correlations[correlation_id]
            
            # Get event details
            events = []
            for event_id in event_ids:
                if self.redis_client:
                    event_key = f"audit:event:{event_id}"
                    event_data = await self.redis_client.hget(event_key, "event_data")
                    if event_data:
                        try:
                            event = AuditEvent.parse_raw(event_data)
                            events.append(event)
                        except Exception:
                            continue
            
            return sorted(events, key=lambda x: x.timestamp)
            
        except Exception as e:
            logger.error("Failed to get event correlation",
                        correlation_id=correlation_id, error=str(e))
            return []
    
    async def generate_compliance_report(
        self, 
        config: ComplianceReportConfig
    ) -> Dict[str, Any]:
        """Generate compliance report"""
        try:
            # Create filter for the report
            filters = AuditFilter(
                start_time=config.start_date,
                end_time=config.end_date,
                event_types=config.include_event_types,
                limit=10000  # High limit for reports
            )
            
            events = await self.search_events(filters)
            
            # Generate report structure
            report = {
                "report_type": config.report_type,
                "jurisdiction": config.jurisdiction,
                "period": {
                    "start": config.start_date.isoformat(),
                    "end": config.end_date.isoformat()
                },
                "generated_at": datetime.utcnow().isoformat(),
                "summary": {
                    "total_events": len(events),
                    "event_types": {},
                    "users": set(),
                    "compliance_violations": 0,
                    "security_alerts": 0
                },
                "events": []
            }
            
            # Process events
            for event in events:
                # Add to summary
                event_type = event.event_type.value
                if event_type not in report["summary"]["event_types"]:
                    report["summary"]["event_types"][event_type] = 0
                report["summary"]["event_types"][event_type] += 1
                
                if event.user_id:
                    report["summary"]["users"].add(event.user_id)
                
                if event.event_type == AuditEventType.COMPLIANCE_VIOLATION:
                    report["summary"]["compliance_violations"] += 1
                
                if event.event_type == AuditEventType.SECURITY_ALERT:
                    report["summary"]["security_alerts"] += 1
                
                # Add event details based on format
                if config.format == "json":
                    report["events"].append(event.dict())
                elif config.format == "csv":
                    # Simplified CSV format
                    report["events"].append({
                        "timestamp": event.timestamp.isoformat(),
                        "event_type": event.event_type.value,
                        "user_id": event.user_id,
                        "description": event.description,
                        "outcome": event.outcome.value
                    })
            
            # Convert set to list for JSON serialization
            report["summary"]["users"] = list(report["summary"]["users"])
            
            return report
            
        except Exception as e:
            logger.error("Failed to generate compliance report", error=str(e))
            return {"error": str(e)}
    
    # Convenience methods for common audit events
    async def log_request_start(
        self, 
        request_id: str, 
        user_id: str, 
        operation: str, 
        timestamp: datetime
    ):
        """Log API request start"""
        await self.log_event(
            AuditEventType.API_REQUEST,
            f"API request started: {operation}",
            user_id=user_id,
            request_id=request_id,
            details={"operation": operation, "phase": "start"},
            severity=AuditSeverity.LOW
        )
    
    async def log_request_end(
        self, 
        request_id: str, 
        user_id: str, 
        operation: str, 
        duration: float, 
        timestamp: datetime
    ):
        """Log API request end"""
        await self.log_event(
            AuditEventType.API_REQUEST,
            f"API request completed: {operation}",
            user_id=user_id,
            request_id=request_id,
            details={"operation": operation, "phase": "end", "duration": duration},
            severity=AuditSeverity.LOW
        )
    
    async def log_request_error(
        self, 
        request_id: str, 
        user_id: str, 
        operation: str, 
        error: str, 
        timestamp: datetime
    ):
        """Log API request error"""
        await self.log_event(
            AuditEventType.API_ERROR,
            f"API request failed: {operation} - {error}",
            user_id=user_id,
            request_id=request_id,
            details={"operation": operation, "error": error},
            severity=AuditSeverity.HIGH,
            outcome=AuditOutcome.ERROR
        )