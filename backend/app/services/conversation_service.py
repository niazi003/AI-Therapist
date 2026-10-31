"""Conversation service — delegates to the LangGraph therapy graph.

Replaces the previous flat safety-review + Letta flow with the
compiled multi-agent LangGraph graph that handles:
  1. Long-term context loading from the Store
  2. Intake safety evaluation
  3. Routing to therapist / follow-up / emergency referral
  4. Periodic memory consolidation
"""
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.langgraph_therapy import (
    get_therapy_graph,
    normalize_country_code,
    safety_review_unavailable_node,
)
from app.services.graph_state import TherapyState

logger = logging.getLogger(__name__)


class ConversationService:
    """Service for handling user conversations via the LangGraph graph."""

    async def process_message(
        self,
        user_id: str,
        message: str,
        user_has_consent: bool,
        db: AsyncSession,
        thread_id: Optional[str] = None,
        country_code: Optional[str] = None,
    ) -> dict:
        """Process a user message through the LangGraph therapy graph.

        Args:
            user_id: The user's UUID.
            message: The raw user message.
            user_has_consent: Whether the user granted AI-processing consent.
            db: Database session (retained for future persistence hooks).
            thread_id: Optional thread ID for checkpointer continuity.

        Returns:
            Dict with workflow, message, clarifying_question, urgent_help_info.
        """
        # --- Consent gate ---
        if not user_has_consent:
            return {
                "workflow": "review_unavailable",
                "message": "Consent is required for AI processing. Please provide consent first.",
                "urgent_help_info": None,
            }

        # Build the initial state for this invocation
        thread = thread_id or f"thread-{user_id}"
        config = {"configurable": {"thread_id": thread}}

        input_state: TherapyState = {
            "user_id": user_id,
            "user_message": message,
            "service_unavailable": False,
            "support_url": None,
        }
        normalized_country_code = normalize_country_code(country_code)
        if normalized_country_code:
            input_state["country_code"] = normalized_country_code

        try:
            graph = get_therapy_graph()
            result = await graph.ainvoke(input_state, config=config)

            if not isinstance(result, dict):
                raise ValueError("Therapy graph returned an invalid result")
            workflow = result.get("workflow")
            ai_response = result.get("ai_response")
            if workflow not in {
                "routine",
                "follow_up",
                "urgent",
                "professional_referral",
                "review_unavailable",
            }:
                raise ValueError("Therapy graph returned an unknown workflow")
            if not isinstance(ai_response, str) or not ai_response.strip():
                raise ValueError("Therapy graph returned an empty response")
            clarifying_question = result.get("clarifying_question")

            urgent_help_info = None
            if workflow == "urgent":
                urgent_help_info = ai_response

            return {
                "workflow": workflow,
                "message": ai_response,
                "clarifying_question": clarifying_question if workflow == "follow_up" else None,
                "urgent_help_info": urgent_help_info,
                "service_unavailable": bool(result.get("service_unavailable", False)),
                "support_url": result.get("support_url"),
            }

        except Exception:
            logger.exception("LangGraph therapy graph invocation failed")
            unavailable = await safety_review_unavailable_node(input_state)
            return {
                "workflow": "review_unavailable",
                "message": unavailable["ai_response"],
                "clarifying_question": None,
                "urgent_help_info": None,
                "service_unavailable": False,
                "support_url": None,
            }


conversation_service = ConversationService()
