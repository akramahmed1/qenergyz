"""
Onboarding Routes

User onboarding, KYC verification, and account setup.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies.auth import get_current_active_user
from ..dependencies.database import get_db
from ..dependencies.rate_limiting import api_rate_limit
from ..models.user import User

router = APIRouter()


@router.get("/status")
async def get_onboarding_status(
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(api_rate_limit)
):
    """Get user onboarding status"""
    
    return {
        "user_id": current_user.id,
        "email_verified": current_user.is_verified,
        "kyc_status": current_user.kyc_status,
        "profile_completed": bool(current_user.company and current_user.job_title),
        "onboarding_complete": current_user.is_verified and current_user.kyc_status == "approved"
    }


@router.post("/kyc")
async def submit_kyc(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(api_rate_limit)
):
    """Submit KYC documentation"""
    
    return {
        "message": "KYC submission endpoint - implementation pending",
        "kyc_status": "pending",
        "reference_id": "pending"
    }


@router.post("/complete")
async def complete_onboarding(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(api_rate_limit)
):
    """Complete user onboarding process"""
    
    return {
        "message": "Complete onboarding endpoint - implementation pending",
        "status": "completed"
    }