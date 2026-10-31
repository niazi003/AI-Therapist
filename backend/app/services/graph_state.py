"""Strictly typed state definitions for the LangGraph therapy graph.

All cross-agent state is defined here using TypedDict to guarantee
consistent memory payloads when queried or updated between the
intake evaluator, active therapist, and emergency referral agents.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional, Sequence
from typing_extensions import TypedDict

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Pydantic models for Store payloads (long-term, cross-thread memory)
# ---------------------------------------------------------------------------

class ClinicalProfile(BaseModel):
    """Long-lived clinical profile stored under
    ["patient", {user_id}, "clinical_profile"]."""
    important_context: str = ""
    goals: str = ""
    challenges: str = ""
    support_preferences: str = ""
    known_triggers: list[str] = Field(default_factory=list)
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class DistressEvent(BaseModel):
    """A single distress/crisis event stored under
    ["patient", {user_id}, "distress_events"]."""
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    severity: Literal["low", "moderate", "high", "critical"] = "moderate"
    description: str = ""
    safety_action_taken: str = ""


class SessionSummary(BaseModel):
    """Compressed conversation summary stored under
    ["patient", {user_id}, "session_summaries"]."""
    session_id: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    summary: str = ""
    key_topics: list[str] = Field(default_factory=list)
    emotional_state: str = ""
    insights: list[str] = Field(default_factory=list)
    action_items: list[str] = Field(default_factory=list)


class MoodEntry(BaseModel):
    """Mood tracking entry stored under
    ["patient", {user_id}, "mood_tracker"]."""
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    mood: str = ""
    intensity: int = 5  # 1-10
    context: str = ""


# ---------------------------------------------------------------------------
# TypedDict for the in-flight graph state (short-term, per-thread)
# ---------------------------------------------------------------------------

class TherapyState(TypedDict, total=False):
    """State passed between nodes in the therapy graph.
    
    Fields:
        user_id: The authenticated patient's UUID.
        user_message: The raw incoming message from the patient.
        conversation_history: Rolling list of {"role": ..., "content": ...} dicts.
        safety_classification: Result of the intake safety review.
        clarifying_question: Optional follow-up question from safety review.
        referral_type: Whether a professional referral is for therapy, medical care, or both.
        country_code: User-confirmed approximate country or explicitly stated country.
        ai_response: The therapist agent's generated response.
        workflow: Current workflow branch.
        service_unavailable: Whether AI response generation failed.
        support_url: Human-support directory to show when AI generation fails.
        needs_consolidation: Flag for the memory consolidation node.
        turn_count: How many user turns have occurred in this thread.
        clinical_context: Serialized clinical profile (injected from Store).
        session_summaries_context: Previous session summaries (injected from Store).
        error: Any error message to surface.
    """
    user_id: str
    user_message: str
    conversation_history: list[dict[str, str]]
    safety_classification: Literal[
        "routine", "follow_up", "urgent", "professional_referral", "review_unavailable"
    ]
    clarifying_question: Optional[str]
    referral_type: Optional[Literal["therapist", "medical", "both"]]
    country_code: Optional[str]
    ai_response: str
    workflow: Literal[
        "routine", "follow_up", "urgent", "professional_referral", "review_unavailable"
    ]
    service_unavailable: bool
    support_url: Optional[str]
    needs_consolidation: bool
    turn_count: int
    clinical_context: str
    session_summaries_context: str
    error: Optional[str]
