"""LangGraph Store initialization and hierarchical namespace helpers.

Uses PostgreSQL-backed storage in the running application and an in-memory
Store only when a graph is created outside application startup. Patient data
is organized into strict namespaces:

  ["patient", {user_id}, "clinical_profile"]
  ["patient", {user_id}, "distress_events"]
  ["patient", {user_id}, "session_summaries"]
  ["patient", {user_id}, "mood_tracker"]
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from langgraph.store.memory import InMemoryStore
from langgraph.store.postgres.aio import AsyncPostgresStore

from app.core.config import settings
from app.services.graph_state import (
    ClinicalProfile,
    DistressEvent,
    MoodEntry,
    SessionSummary,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singleton store instance
# ---------------------------------------------------------------------------
_store: InMemoryStore | AsyncPostgresStore | None = None
_store_context: Any = None


def get_store() -> InMemoryStore | AsyncPostgresStore:
    """Return the configured Store, using in-memory storage before app startup."""
    global _store
    if _store is None:
        _store = InMemoryStore()
        logger.info("LangGraph in-memory Store initialized")
    return _store


async def initialize_store() -> None:
    """Open and initialize the PostgreSQL-backed long-term Store."""
    global _store, _store_context
    if _store_context is not None:
        return

    context = AsyncPostgresStore.from_conn_string(settings.DATABASE_URL_SYNC)
    store = await context.__aenter__()
    try:
        await store.setup()
    except Exception as exc:
        await context.__aexit__(type(exc), exc, exc.__traceback__)
        raise

    _store_context = context
    _store = store
    logger.info("PostgreSQL LangGraph Store initialized")


async def close_store() -> None:
    """Close the PostgreSQL-backed Store during application shutdown."""
    global _store, _store_context
    if _store_context is not None:
        await _store_context.__aexit__(None, None, None)
        _store_context = None
        _store = None
        logger.info("PostgreSQL LangGraph Store closed")


# ---------------------------------------------------------------------------
# Namespace helpers – read / write for each data category
# ---------------------------------------------------------------------------

def _ns_clinical(user_id: str) -> tuple[str, ...]:
    return ("patient", user_id, "clinical_profile")


def _ns_distress(user_id: str) -> tuple[str, ...]:
    return ("patient", user_id, "distress_events")


def _ns_sessions(user_id: str) -> tuple[str, ...]:
    return ("patient", user_id, "session_summaries")


def _ns_mood(user_id: str) -> tuple[str, ...]:
    return ("patient", user_id, "mood_tracker")


# --- Clinical Profile ---

async def get_clinical_profile(user_id: str) -> ClinicalProfile:
    """Retrieve the patient's clinical profile from the Store."""
    store = get_store()
    item = await store.aget(_ns_clinical(user_id), "profile")
    if item:
        return ClinicalProfile(**item.value)
    return ClinicalProfile()


async def upsert_clinical_profile(user_id: str, profile: ClinicalProfile) -> None:
    """Write or overwrite the clinical profile."""
    store = get_store()
    profile.updated_at = datetime.utcnow().isoformat()
    await store.aput(_ns_clinical(user_id), "profile", profile.model_dump())
    logger.info(f"Upserted clinical profile for user {user_id}")


# --- Distress Events ---

async def add_distress_event(user_id: str, event: DistressEvent) -> None:
    """Append a distress event to the patient's record."""
    store = get_store()
    event_id = f"evt-{uuid4().hex[:8]}"
    await store.aput(_ns_distress(user_id), event_id, event.model_dump())
    logger.info(f"Recorded distress event {event_id} for user {user_id}")


async def get_distress_events(user_id: str, limit: int = 10) -> list[DistressEvent]:
    """Return the most recent distress events."""
    store = get_store()
    items = await store.asearch(_ns_distress(user_id), limit=limit)
    return [DistressEvent(**item.value) for item in items]


# --- Session Summaries ---

async def add_session_summary(user_id: str, summary: SessionSummary) -> None:
    """Save a compressed session summary."""
    store = get_store()
    summary_id = summary.session_id or f"sess-{uuid4().hex[:8]}"
    await store.aput(_ns_sessions(user_id), summary_id, summary.model_dump())
    logger.info(f"Saved session summary {summary_id} for user {user_id}")


async def get_session_summaries(user_id: str, limit: int = 5) -> list[SessionSummary]:
    """Return the most recent session summaries."""
    store = get_store()
    items = await store.asearch(_ns_sessions(user_id), limit=limit)
    return [SessionSummary(**item.value) for item in items]


# --- Mood Tracker ---

async def add_mood_entry(user_id: str, entry: MoodEntry) -> None:
    """Append a mood tracking entry."""
    store = get_store()
    entry_id = f"mood-{uuid4().hex[:8]}"
    await store.aput(_ns_mood(user_id), entry_id, entry.model_dump())


async def get_mood_history(user_id: str, limit: int = 20) -> list[MoodEntry]:
    """Return recent mood entries."""
    store = get_store()
    items = await store.asearch(_ns_mood(user_id), limit=limit)
    return [MoodEntry(**item.value) for item in items]


# --- Bulk read (for Memory API endpoint) ---

async def get_all_memory_blocks(user_id: str) -> list[dict[str, Any]]:
    """Return all stored memory for a user, formatted as memory blocks."""
    blocks: list[dict[str, Any]] = []

    # Clinical profile
    profile = await get_clinical_profile(user_id)
    if profile.important_context:
        blocks.append({
            "id": "context",
            "memory_type": "Important Context",
            "content": profile.important_context,
            "created_at": profile.updated_at,
        })
    if profile.goals:
        blocks.append({
            "id": "goals",
            "memory_type": "Goals",
            "content": profile.goals,
            "created_at": profile.updated_at,
        })
    if profile.challenges:
        blocks.append({
            "id": "challenges",
            "memory_type": "Challenges",
            "content": profile.challenges,
            "created_at": profile.updated_at,
        })
    if profile.support_preferences:
        blocks.append({
            "id": "support",
            "memory_type": "Support Preferences",
            "content": profile.support_preferences,
            "created_at": profile.updated_at,
        })
    if profile.known_triggers:
        blocks.append({
            "id": "triggers",
            "memory_type": "Known Triggers",
            "content": ", ".join(profile.known_triggers),
            "created_at": profile.updated_at,
        })

    # Session summaries
    for s in await get_session_summaries(user_id, limit=5):
        blocks.append({
            "id": s.session_id,
            "memory_type": f"Session Summary ({s.timestamp[:10]})",
            "content": s.summary,
            "created_at": s.timestamp,
        })

    # Distress events
    for e in await get_distress_events(user_id, limit=5):
        blocks.append({
            "id": f"distress-{e.timestamp}",
            "memory_type": f"Distress Event ({e.severity})",
            "content": e.description,
            "created_at": e.timestamp,
        })

    for mood in await get_mood_history(user_id, limit=20):
        blocks.append({
            "id": f"mood-{mood.timestamp}",
            "memory_type": f"Mood ({mood.intensity}/10)",
            "content": mood.mood,
            "created_at": mood.timestamp,
        })

    return blocks


async def delete_all_memory(user_id: str) -> None:
    """Purge all stored memory for a user across all namespaces."""
    store = get_store()
    for ns_fn in (_ns_clinical, _ns_distress, _ns_sessions, _ns_mood):
        ns = ns_fn(user_id)
        items = await store.asearch(ns, limit=1000)
        for item in items:
            await store.adelete(ns, item.key)
    logger.info(f"Deleted all memory for user {user_id}")
