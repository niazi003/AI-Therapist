"""Appointment booking API endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.user import (
    ProviderResponse,
    ProviderSlot,
    AppointmentCreate,
    AppointmentResponse,
)
from app.core.security import get_current_user
from app.services.appointment_service import appointment_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["appointments"])


@router.get("/providers", response_model=list[ProviderResponse])
async def search_providers(
    specialty: str | None = None,
    location: str | None = None,
):
    """Search for mental health providers."""
    providers = await appointment_service.search_providers(specialty, location)
    return providers


@router.get("/providers/{provider_id}/slots")
async def get_provider_slots(provider_id: str):
    """Get available slots for a provider."""
    slots = await appointment_service.get_provider_slots(provider_id)
    return {
        "provider_id": provider_id,
        "slots": slots,
        "is_simulated": True,
    }


@router.post("/appointments", response_model=AppointmentResponse)
async def book_appointment(
    booking: AppointmentCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Book an appointment with a provider."""
    result = await appointment_service.book_appointment(
        db=db,
        user_id=current_user["user_id"],
        provider_id=booking.provider_id,
        slot_id=booking.slot_id,
        idempotency_key=booking.idempotency_key,
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error"),
        )
    
    return result["appointment"]


@router.get("/appointments")
async def get_appointments(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's appointments."""
    appointments = await appointment_service.get_user_appointments(
        db, current_user["user_id"]
    )
    return appointments


@router.post("/appointments/{appointment_id}/cancel")
async def cancel_appointment(
    appointment_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel an appointment."""
    result = await appointment_service.cancel_appointment(
        db, current_user["user_id"], appointment_id
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error"),
        )
    
    return result