"""
Authentication Schemas

Pydantic models for authentication requests and responses.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class TokenResponse(BaseModel):
    """JWT token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class UserLogin(BaseModel):
    """User login request"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class UserRegister(BaseModel):
    """User registration request"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    company: Optional[str] = Field(None, max_length=200)
    job_title: Optional[str] = Field(None, max_length=100)


class PasswordChange(BaseModel):
    """Password change request"""
    current_password: str = Field(..., min_length=8, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


class PasswordReset(BaseModel):
    """Password reset request"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation"""
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


class TokenData(BaseModel):
    """Token validation data"""
    user_id: str
    type: str
    payload: dict = Field(default_factory=dict)