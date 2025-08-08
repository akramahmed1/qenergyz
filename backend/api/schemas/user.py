"""
User Schemas

Pydantic models for user management.
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class UserProfile(BaseModel):
    """User profile information"""
    id: str
    email: str
    first_name: str
    last_name: str
    role: str
    is_verified: bool
    is_active: bool
    phone: Optional[str] = None
    company: Optional[str] = None
    job_title: Optional[str] = None
    region: str
    kyc_status: str
    last_login_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """User profile update"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    company: Optional[str] = Field(None, max_length=200)
    job_title: Optional[str] = Field(None, max_length=100)
    region: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None


class UserList(BaseModel):
    """User list response"""
    users: List[UserProfile]
    total: int
    page: int
    size: int
    pages: int


class UserCreate(BaseModel):
    """Admin user creation"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    role: str = Field(default="user")
    phone: Optional[str] = Field(None, max_length=20)
    company: Optional[str] = Field(None, max_length=200)
    job_title: Optional[str] = Field(None, max_length=100)
    region: str = Field(default="middle_east")
    is_verified: bool = Field(default=False)