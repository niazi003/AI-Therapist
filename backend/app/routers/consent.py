"""Consent management API endpoints."""
import logging
from uuid import uuid4
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models.user import User, ConsentRecord
from app.schemas.user import ConsentCreate, ConsentUpdate, ConsentResponse
from app.core.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["consent"])

# Define consent purposes
CONSENT_PURPOSES = {
    "ai_processing": "AI-powered conversation and support",
    "memory_storage": "Persistent memory of preferences and conversation context",
    "appointment_booking": "Booking appointments with mental health providers",
}


@router.get("/consent", response_model=list[ConsentResponse])
async def get_consent(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's consent records."""
    result = await db.execute(
        select(ConsentRecord).where(
            ConsentRecord.user_id == current_user["user_id"]
        )
    )
    consents = result.scalars().all()
    return consents


@router.put("/consent", response_model=ConsentResponse)
async def update_consent(
    consent_data: ConsentCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update user's consent for a specific purpose."""
    # Validate purpose
    if consent_data.purpose not in CONSENT_PURPOSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid purpose. Valid purposes: {list(CONSENT_PURPOSES.keys())}",
        )
    
    # Check for existing consent
    result = await db.execute(
        select(ConsentRecord).where(
            ConsentRecord.user_id == current_user["user_id"],
            ConsentRecord.purpose == consent_data.purpose,
        )
    )
    existing = result.scalar_one_or_none()
    
    now = datetime.utcnow()
    
    if existing:
        # Update existing consent
        existing.granted = consent_data.granted
        existing.policy_version = consent_data.policy_version
        if consent_data.granted and not existing.granted_at:
            existing.granted_at = now
        elif not consent_data.granted:
            existing.withdrawn_at = now
        consent = existing
    else:
        # Create new consent
        consent = ConsentRecord(
            id=str(uuid4()),
            user_id=current_user["user_id"],
            purpose=consent_data.purpose,
            granted=consent_data.granted,
            policy_version=consent_data.policy_version,
            granted_at=now if consent_data.granted else None,
        )
        db.add(consent)
    
    await db.commit()
    await db.refresh(consent)
    
    return consent


@router.get("/consent/required")
async def get_required_consents():
    """Get list of required consent purposes."""
    return {
        "purposes": CONSENT_PURPOSES,
        "required_for_ai": ["ai_processing"],
    }


async def check_user_consent(
    user_id: str,
    purpose: str,
    db: AsyncSession,
) -> bool:
    """Check if user has given consent for a specific purpose."""
    result = await db.execute(
        select(ConsentRecord).where(
            ConsentRecord.user_id == user_id,
            ConsentRecord.purpose == purpose,
            ConsentRecord.granted == True,
        )
    )
    return result.scalar_one_or_none() is not None