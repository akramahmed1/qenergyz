"""
Common Schemas

Shared Pydantic models for API requests and responses.
"""

from typing import Optional, Any, Dict, List
from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = Field(1, ge=1, le=1000, description="Page number")
    size: int = Field(20, ge=1, le=100, description="Page size")
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size
    
    @property
    def limit(self) -> int:
        return self.size


class BaseResponse(BaseModel):
    """Base response model"""
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Error response model"""
    success: bool = False
    error: str
    status_code: int
    details: Optional[Dict[str, Any]] = None


class HealthCheck(BaseModel):
    """Health check response"""
    status: str
    version: str
    environment: str
    timestamp: float
    services: Optional[Dict[str, str]] = None


class APIStatus(BaseModel):
    """API status response"""
    api_version: str
    status: str
    features: List[str]
    uptime: Optional[float] = None