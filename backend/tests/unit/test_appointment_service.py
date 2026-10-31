"""Tests for provider availability and appointment adapter behavior."""
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.appointment_service import AppointmentService, generate_slots


class TestProviderAvailability:
    def test_generated_slots_use_business_hours(self):
        slots = generate_slots("provider-test")

        assert slots
        assert all(9 <= slot["start_time"].hour < 17 for slot in slots)
        assert all(
            slot["end_time"] - slot["start_time"] == timedelta(hours=1)
            for slot in slots
        )

    @pytest.mark.asyncio
    async def test_booking_rejects_slots_not_offered_by_provider(self):
        provider_directory = MagicMock()
        provider_directory.get_provider = AsyncMock(
            return_value={"id": "provider-test", "name": "Test Provider"}
        )
        provider_directory.get_provider_slots = AsyncMock(
            return_value=[{
                "slot_id": "provider-test-slot-valid",
                "start_time": datetime.now() + timedelta(days=1),
                "end_time": datetime.now() + timedelta(days=1, hours=1),
                "is_available": True,
            }]
        )
        db = MagicMock()
        db.execute = AsyncMock(
            return_value=SimpleNamespace(scalar_one_or_none=lambda: None)
        )
        db.commit = AsyncMock()

        service = AppointmentService(provider_directory)
        result = await service.book_appointment(
            db=db,
            user_id="user-test",
            provider_id="provider-test",
            slot_id="provider-test-slot-not-offered",
            idempotency_key="booking-test",
        )

        assert result["success"] is False
        assert result["error"] == "Slot is no longer available"
        db.add.assert_not_called()
        db.commit.assert_not_awaited()
