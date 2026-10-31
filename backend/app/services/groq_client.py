"""Groq client service for AI inference.

Provides async and sync chat completion methods used by the LangGraph
therapy graph nodes (intake evaluator, active therapist, memory
consolidation).
"""
import logging
from typing import Optional

from groq import AsyncGroq, Groq
from groq._exceptions import APIConnectionError, RateLimitError, APIStatusError

from app.core.config import settings

logger = logging.getLogger(__name__)


class GroqClient:
    """Client for Groq API interactions."""

    def __init__(self):
        self._sync_client: Optional[Groq] = None
        self._async_client: Optional[AsyncGroq] = None

    @property
    def client(self) -> Groq:
        """Get or create synchronous Groq client."""
        if self._sync_client is None:
            if not settings.GROQ_API_KEY:
                raise ValueError("GROQ_API_KEY not configured")
            self._sync_client = Groq(api_key=settings.GROQ_API_KEY)
        return self._sync_client

    @property
    def async_client(self) -> AsyncGroq:
        """Get or create asynchronous Groq client."""
        if self._async_client is None:
            if not settings.GROQ_API_KEY:
                raise ValueError("GROQ_API_KEY not configured")
            self._async_client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        return self._async_client

    def is_configured(self) -> bool:
        """Check if Groq is properly configured."""
        return bool(settings.GROQ_API_KEY)

    async def chat_completion(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[list[dict]] = None,
        response_format: Optional[dict[str, str]] = None,
    ) -> str:
        """Send an async chat completion request to Groq.

        Args:
            messages: List of {"role": ..., "content": ...} dicts.
            model: Override model name (defaults to GROQ_CHAT_MODEL).
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in the response.
            tools: Optional Groq-hosted tools available to the model.

        Returns:
            The assistant's response text.
        """
        if not self.is_configured():
            raise ValueError("Groq is not configured")

        response = await self.async_client.chat.completions.create(
            model=model or settings.GROQ_CHAT_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
            response_format=response_format,
            timeout=settings.GROQ_TIMEOUT_SECONDS,
        )
        return response.choices[0].message.content

    def chat_completion_sync(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Send a synchronous chat completion request to Groq."""
        if not self.is_configured():
            raise ValueError("Groq is not configured")

        response = self.client.chat.completions.create(
            model=model or settings.GROQ_CHAT_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=settings.GROQ_TIMEOUT_SECONDS,
        )
        return response.choices[0].message.content


# Singleton instance used by all LangGraph nodes
groq_client = GroqClient()