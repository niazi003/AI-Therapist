"""Unit tests for the Groq client service."""
import pytest
from unittest.mock import AsyncMock
from app.services.groq_client import GroqClient, groq_client


class TestGroqClient:
    """Tests for GroqClient class."""

    def test_is_configured_with_api_key(self, monkeypatch):
        """Test that client is configured when API key is set."""
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        client = GroqClient()
        # Force settings reload
        from app.core.config import settings
        monkeypatch.setattr(settings, "GROQ_API_KEY", "test-key")
        assert client.is_configured() is True

    def test_is_configured_without_api_key(self, monkeypatch):
        """Test that client is not configured without API key."""
        from app.core.config import settings
        monkeypatch.setattr(settings, "GROQ_API_KEY", None)
        client = GroqClient()
        assert client.is_configured() is False

    @pytest.mark.asyncio
    async def test_chat_completion_without_config(self, monkeypatch):
        """Test that chat completion raises without API key."""
        from app.core.config import settings
        monkeypatch.setattr(settings, "GROQ_API_KEY", None)
        client = GroqClient()
        with pytest.raises(ValueError, match="not configured"):
            await client.chat_completion([{"role": "user", "content": "hello"}])

    @pytest.mark.asyncio
    async def test_chat_completion_success(self, monkeypatch):
        """Test successful chat completion returns content."""
        from app.core.config import settings
        monkeypatch.setattr(settings, "GROQ_API_KEY", "test-key")

        client = GroqClient()

        # Mock the async client response
        mock_choice = type("Choice", (), {"message": type("Msg", (), {"content": "Hello there!"})()})()
        mock_response = type("Response", (), {"choices": [mock_choice]})()

        mock_async = AsyncMock()
        mock_async.chat.completions.create = AsyncMock(return_value=mock_response)
        client._async_client = mock_async

        result = await client.chat_completion(
            messages=[{"role": "user", "content": "hi"}],
            temperature=0.5,
        )
        assert result == "Hello there!"

    @pytest.mark.asyncio
    async def test_chat_completion_uses_default_model(self, monkeypatch):
        """Test that default model from settings is used when none specified."""
        from app.core.config import settings
        monkeypatch.setattr(settings, "GROQ_API_KEY", "test-key")
        monkeypatch.setattr(settings, "GROQ_CHAT_MODEL", "test-model")

        client = GroqClient()

        mock_choice = type("Choice", (), {"message": type("Msg", (), {"content": "ok"})()})()
        mock_response = type("Response", (), {"choices": [mock_choice]})()

        mock_async = AsyncMock()
        mock_async.chat.completions.create = AsyncMock(return_value=mock_response)
        client._async_client = mock_async

        await client.chat_completion(
            messages=[{"role": "user", "content": "hi"}],
        )

        call_kwargs = mock_async.chat.completions.create.call_args
        assert call_kwargs.kwargs["model"] == "test-model"

    @pytest.mark.asyncio
    async def test_chat_completion_model_override(self, monkeypatch):
        """Test that a specific model can override the default."""
        from app.core.config import settings
        monkeypatch.setattr(settings, "GROQ_API_KEY", "test-key")

        client = GroqClient()

        mock_choice = type("Choice", (), {"message": type("Msg", (), {"content": "ok"})()})()
        mock_response = type("Response", (), {"choices": [mock_choice]})()

        mock_async = AsyncMock()
        mock_async.chat.completions.create = AsyncMock(return_value=mock_response)
        client._async_client = mock_async

        await client.chat_completion(
            messages=[{"role": "user", "content": "hi"}],
            model="custom-model",
        )

        call_kwargs = mock_async.chat.completions.create.call_args
        assert call_kwargs.kwargs["model"] == "custom-model"

    @pytest.mark.asyncio
    async def test_chat_completion_passes_optional_tools(self, monkeypatch):
        from app.core.config import settings
        monkeypatch.setattr(settings, "GROQ_API_KEY", "test-key")

        client = GroqClient()
        mock_choice = type("Choice", (), {"message": type("Msg", (), {"content": "ok"})()})()
        mock_response = type("Response", (), {"choices": [mock_choice]})()
        mock_async = AsyncMock()
        mock_async.chat.completions.create = AsyncMock(return_value=mock_response)
        client._async_client = mock_async

        tools = [{"type": "browser_search"}]
        await client.chat_completion(
            messages=[{"role": "user", "content": "Find a therapist"}],
            tools=tools,
        )

        assert mock_async.chat.completions.create.call_args.kwargs["tools"] == tools

    @pytest.mark.asyncio
    async def test_chat_completion_passes_json_response_format(self, monkeypatch):
        from app.core.config import settings
        monkeypatch.setattr(settings, "GROQ_API_KEY", "test-key")

        client = GroqClient()
        mock_choice = type("Choice", (), {"message": type("Msg", (), {"content": "{}"})()})()
        mock_response = type("Response", (), {"choices": [mock_choice]})()
        mock_async = AsyncMock()
        mock_async.chat.completions.create = AsyncMock(return_value=mock_response)
        client._async_client = mock_async

        await client.chat_completion(
            messages=[{"role": "user", "content": "Return JSON"}],
            response_format={"type": "json_object"},
        )

        assert mock_async.chat.completions.create.call_args.kwargs["response_format"] == {
            "type": "json_object"
        }

    def test_sync_client_raises_without_config(self, monkeypatch):
        """Test that sync client property raises without API key."""
        from app.core.config import settings
        monkeypatch.setattr(settings, "GROQ_API_KEY", None)
        client = GroqClient()
        with pytest.raises(ValueError, match="not configured"):
            _ = client.client

    def test_async_client_raises_without_config(self, monkeypatch):
        """Test that async client property raises without API key."""
        from app.core.config import settings
        monkeypatch.setattr(settings, "GROQ_API_KEY", None)
        client = GroqClient()
        with pytest.raises(ValueError, match="not configured"):
            _ = client.async_client