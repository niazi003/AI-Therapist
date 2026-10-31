"""Unit tests for API endpoints."""
import ipaddress

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock

from app.main import app
from app.core.security import get_current_user


@pytest_asyncio.fixture
async def client():
    """Create test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestHealthEndpoint:
    """Tests for health endpoint."""

    @pytest.mark.asyncio
    async def test_health_check_returns_status(self, client):
        """Test health check returns status."""
        response = await client.get("/api/v1/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "services" in data

    @pytest.mark.asyncio
    async def test_health_check_includes_version(self, client):
        """Test health check includes version."""
        response = await client.get("/api/v1/health")
        data = response.json()
        assert data["version"] == "0.2.0"


class TestLocationEndpoint:
    """Tests for the optional country-estimation endpoint."""

    @pytest.mark.asyncio
    async def test_country_estimate_uses_forwarded_public_ip(self, client):
        with patch(
            "app.routers.location.lookup_country_code",
            new=AsyncMock(return_value="CA"),
        ) as lookup:
            response = await client.get(
                "/api/v1/location/country",
                headers={"X-Real-IP": "8.8.8.8"},
            )

        assert response.status_code == 200
        assert response.json() == {"country_code": "CA"}
        lookup.assert_awaited_once_with(ipaddress.ip_address("8.8.8.8"))

    @pytest.mark.asyncio
    async def test_country_estimate_returns_service_unavailable_on_provider_error(self, client):
        import httpx

        with patch(
            "app.routers.location.lookup_country_code",
            new=AsyncMock(side_effect=httpx.ConnectError("provider unavailable")),
        ):
            response = await client.get("/api/v1/location/country")

        assert response.status_code == 503
        assert "temporarily unavailable" in response.json()["detail"]


class TestAuthEndpoint:
    """Tests for authentication endpoints."""

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        response = await client.post(
            "/api/v1/login",
            json={"email": "invalid@test.com", "password": "wrong"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_register_validation(self, client):
        """Test registration validates input."""
        response = await client.post(
            "/api/v1/register",
            json={"email": "invalid", "password": "short"}
        )
        assert response.status_code == 422  # Validation error


class TestConsentEndpoint:
    """Tests for consent endpoints."""

    @pytest.mark.asyncio
    async def test_get_consent_requires_auth(self, client):
        """Test get consent requires authentication."""
        response = await client.get("/api/v1/consent")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_consent_requires_auth(self, client):
        """Test update consent requires authentication."""
        response = await client.put(
            "/api/v1/consent",
            json={"purpose": "ai_processing", "granted": True}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_required_consents_is_public(self, client):
        """Test that required consents endpoint works without auth."""
        response = await client.get("/api/v1/consent/required")
        assert response.status_code == 200
        data = response.json()
        assert "purposes" in data
        assert "ai_processing" in data["purposes"]


class TestChatEndpoint:
    """Tests for chat endpoints."""

    @pytest.mark.asyncio
    async def test_chat_requires_auth(self, client):
        """Test chat requires authentication."""
        response = await client.post(
            "/api/v1/chat",
            json={"message": "Hello"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_chat_validates_empty_message(self, client):
        """Test chat rejects empty messages."""
        app.dependency_overrides[get_current_user] = lambda: {"user_id": "test-user"}
        try:
            response = await client.post(
                "/api/v1/chat",
                json={"message": ""},
            )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
        assert response.status_code == 422


class TestMemoryEndpoint:
    """Tests for memory endpoints."""

    @pytest.mark.asyncio
    async def test_get_memory_requires_auth(self, client):
        """Test get memory requires authentication."""
        response = await client.get("/api/v1/memory")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_memory_requires_auth(self, client):
        """Test delete memory requires authentication."""
        response = await client.delete("/api/v1/memory")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_memory_clears_store_and_checkpoint(self, client):
        """Deleting all memory also removes the current short-term thread."""
        app.dependency_overrides[get_current_user] = lambda: {"user_id": "test-user"}
        checkpointer = AsyncMock()
        with (
            patch("app.routers.memory.delete_all_memory", new=AsyncMock()) as delete_store,
            patch("app.routers.memory.get_checkpointer", return_value=checkpointer),
        ):
            try:
                response = await client.delete("/api/v1/memory")
            finally:
                app.dependency_overrides.pop(get_current_user, None)

        assert response.status_code == 200
        delete_store.assert_awaited_once_with("test-user")
        checkpointer.adelete_thread.assert_awaited_once_with("thread-test-user")

    @pytest.mark.asyncio
    async def test_end_conversation_clears_only_short_term_state(self, client):
        app.dependency_overrides[get_current_user] = lambda: {"user_id": "test-user"}
        checkpointer = AsyncMock()
        with patch("app.routers.memory.get_checkpointer", return_value=checkpointer):
            try:
                response = await client.post("/api/v1/memory/end-conversation")
            finally:
                app.dependency_overrides.pop(get_current_user, None)

        assert response.status_code == 200
        checkpointer.adelete_thread.assert_awaited_once_with("thread-test-user")


class TestAppointmentsEndpoint:
    """Tests for appointment endpoints."""

    @pytest.mark.asyncio
    async def test_search_providers_without_auth(self, client):
        """Test search providers works without auth."""
        response = await client.get("/api/v1/providers")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_provider_slots_without_auth(self, client):
        """Test get provider slots works without auth."""
        response = await client.get("/api/v1/providers/provider-001/slots")
        assert response.status_code == 200

        data = response.json()
        assert "slots" in data
        assert data["is_simulated"] is True