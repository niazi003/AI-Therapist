"""Appointment service for provider search and booking."""
import logging
from uuid import uuid4
from datetime import datetime, timedelta
from typing import Any, Optional, Protocol

from app.db.models.user import Appointment
from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# Example data only; these are not real providers or actual appointments.
SIMULATED_PROVIDERS = [
    {
        "id": "provider-001",
        "name": "Example Provider 1 (Simulated)",
        "specialty": "Clinical Psychology",
        "location": "Example location (not a real practice)",
        "description": "Demonstration listing only; not a real clinician",
        "fee": "Example only",
    },
    {
        "id": "provider-002",
        "name": "Example Provider 2 (Simulated)",
        "specialty": "Psychiatry",
        "location": "Example location (not a real practice)",
        "description": "Demonstration listing only; not a real clinician",
        "fee": "Example only",
    },
    {
        "id": "provider-003",
        "name": "Example Provider 3 (Simulated)",
        "specialty": "Licensed Clinical Social Worker",
        "location": "Example location (not a real practice)",
        "description": "Demonstration listing only; not a real clinician",
        "fee": "Example only",
    },
]


class ProviderDirectory(Protocol):
    """Adapter contract for a provider directory or booking API."""

    async def search_providers(
        self,
        specialty: Optional[str] = None,
        location: Optional[str] = None,
    ) -> list[dict[str, Any]]: ...

    async def get_provider(self, provider_id: str) -> Optional[dict[str, Any]]: ...

    async def get_provider_slots(self, provider_id: str) -> list[dict[str, Any]]: ...


def generate_slots(provider_id: str, days_ahead: int = 7) -> list[dict]:
    """Generate simulated availability slots."""
    slots = []
    base_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    
    for day in range(days_ahead):
        for hour in range(8):  # 9 AM to 5 PM
            slot_time = base_time + timedelta(days=day, hours=hour)
            if slot_time > datetime.now():
                slot_id = f"{provider_id}-slot-{slot_time.isoformat()}"
                slots.append({
                    "slot_id": slot_id,
                    "start_time": slot_time,
                    "end_time": slot_time + timedelta(hours=1),
                    "is_available": True,
                })
    
    return slots


class SimulatedProviderDirectory:
    """Local provider adapter used until a real directory is selected."""

    async def search_providers(
        self,
        specialty: Optional[str] = None,
        location: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        providers = SIMULATED_PROVIDERS.copy()
        if specialty:
            providers = [
                provider for provider in providers
                if specialty.lower() in provider["specialty"].lower()
            ]
        if location:
            providers = [
                provider for provider in providers
                if location.lower() in provider["location"].lower()
            ]

        return [
            {
                **provider,
                "slots": generate_slots(provider["id"]),
                "is_simulated": True,
            }
            for provider in providers
        ]

    async def get_provider(self, provider_id: str) -> Optional[dict[str, Any]]:
        return next(
            (provider.copy() for provider in SIMULATED_PROVIDERS
             if provider["id"] == provider_id),
            None,
        )

    async def get_provider_slots(self, provider_id: str) -> list[dict[str, Any]]:
        if await self.get_provider(provider_id) is None:
            return []
        return generate_slots(provider_id)


class AppointmentService:
    """Service for managing appointments with mental health providers."""

    def __init__(self, provider_directory: Optional[ProviderDirectory] = None):
        self.provider_directory = provider_directory or SimulatedProviderDirectory()
    
    async def search_providers(
        self,
        specialty: Optional[str] = None,
        location: Optional[str] = None,
    ) -> list[dict]:
        """
        Search for mental health providers.
        
        Args:
            specialty: Optional specialty filter
            location: Optional location filter
            
        Returns:
            List of providers with availability
        """
        return await self.provider_directory.search_providers(specialty, location)
    
    async def get_provider_slots(self, provider_id: str) -> list[dict]:
        """Get available slots for a specific provider."""
        return await self.provider_directory.get_provider_slots(provider_id)
    
    async def book_appointment(
        self,
        db: AsyncSession,
        user_id: str,
        provider_id: str,
        slot_id: str,
        idempotency_key: str,
    ) -> dict:
        """
        Book an appointment (simulated).
        
        Args:
            db: Database session
            user_id: The user ID
            provider_id: The provider ID
            slot_id: The slot ID
            idempotency_key: Key to prevent duplicate bookings
            
        Returns:
            Booking result
        """
        # Check for existing appointment with same idempotency key
        from sqlalchemy import select
        existing = await db.execute(
            select(Appointment).where(
                Appointment.idempotency_key == idempotency_key
            )
        )
        if existing.scalar_one_or_none():
            logger.warning(f"Duplicate appointment attempt: {idempotency_key}")
            return {
                "success": False,
                "error": "This appointment has already been booked",
            }
        
        provider = await self.provider_directory.get_provider(provider_id)
        if not provider:
            return {
                "success": False,
                "error": "Provider not found",
            }

        slot = next(
            (
                available_slot
                for available_slot in await self.provider_directory.get_provider_slots(provider_id)
                if available_slot["slot_id"] == slot_id and available_slot["is_available"]
            ),
            None,
        )
        if slot is None:
            return {
                "success": False,
                "error": "Slot is no longer available",
            }
        slot_time = slot["start_time"]
        
        # Create appointment record
        appointment = Appointment(
            id=str(uuid4()),
            user_id=user_id,
            provider_id=provider_id,
            provider_name=provider["name"],
            slot_id=slot_id,
            appointment_time=slot_time,
            status="confirmed",
            is_simulated=provider.get("is_simulated", True),
            external_confirmation=f"simulated-{uuid4().hex[:8]}",
            idempotency_key=idempotency_key,
        )
        
        db.add(appointment)
        await db.commit()
        
        return {
            "success": True,
            "appointment": {
                "id": appointment.id,
                "provider_id": provider_id,
                "provider_name": provider["name"],
                "appointment_time": slot_time.isoformat(),
                "status": "confirmed",
                "is_simulated": True,
                "external_confirmation": appointment.external_confirmation,
            },
            "disclaimer": "This is a simulated booking for demonstration purposes",
        }
    
    async def get_user_appointments(
        self,
        db: AsyncSession,
        user_id: str,
    ) -> list[dict]:
        """Get appointments for a user."""
        from sqlalchemy import select
        result = await db.execute(
            select(Appointment)
            .where(Appointment.user_id == user_id)
            .order_by(Appointment.appointment_time)
        )
        appointments = result.scalars().all()
        
        return [
            {
                "id": a.id,
                "provider_id": a.provider_id,
                "provider_name": a.provider_name,
                "appointment_time": a.appointment_time.isoformat(),
                "status": a.status,
                "is_simulated": a.is_simulated,
            }
            for a in appointments
        ]
    
    async def cancel_appointment(
        self,
        db: AsyncSession,
        user_id: str,
        appointment_id: str,
    ) -> dict:
        """Cancel an appointment."""
        from sqlalchemy import select
        result = await db.execute(
            select(Appointment).where(
                Appointment.id == appointment_id,
                Appointment.user_id == user_id,
            )
        )
        appointment = result.scalar_one_or_none()
        
        if not appointment:
            return {
                "success": False,
                "error": "Appointment not found",
            }
        
        if appointment.status == "cancelled":
            return {
                "success": False,
                "error": "Appointment already cancelled",
            }
        
        appointment.status = "cancelled"
        await db.commit()
        
        return {
            "success": True,
            "message": "Appointment cancelled",
        }


appointment_service = AppointmentService()