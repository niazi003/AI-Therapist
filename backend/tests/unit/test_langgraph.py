"""Unit tests for the LangGraph therapy graph and store components."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.graph_state import (
    ClinicalProfile,
    DistressEvent,
    MoodEntry,
    SessionSummary,
    TherapyState,
)
from app.services.graph_store import (
    get_store,
    get_clinical_profile,
    upsert_clinical_profile,
    add_distress_event,
    get_distress_events,
    add_session_summary,
    get_session_summaries,
    add_mood_entry,
    get_mood_history,
    get_all_memory_blocks,
    delete_all_memory,
)
from app.services import graph_store


class TestGraphState:
    """Tests for typed state and store payload models."""

    def test_clinical_profile_defaults(self):
        """Test that ClinicalProfile has sensible defaults."""
        profile = ClinicalProfile()
        assert profile.important_context == ""
        assert profile.goals == ""
        assert profile.challenges == ""
        assert profile.support_preferences == ""
        assert profile.known_triggers == []
        assert profile.updated_at  # should have a timestamp

    def test_distress_event_creation(self):
        """Test creating a distress event with all fields."""
        event = DistressEvent(
            severity="high",
            description="Patient expressed suicidal ideation",
            safety_action_taken="Crisis resources provided",
        )
        assert event.severity == "high"
        assert event.timestamp  # auto-populated

    def test_session_summary_creation(self):
        """Test creating a session summary."""
        summary = SessionSummary(
            session_id="sess-abc123",
            summary="Patient discussed work stress and anxiety.",
            key_topics=["work", "anxiety"],
            emotional_state="anxious",
            insights=["Patient recognizes work as primary stressor"],
            action_items=["Try breathing exercises before meetings"],
        )
        assert summary.session_id == "sess-abc123"
        assert len(summary.key_topics) == 2

    def test_mood_entry_creation(self):
        """Test creating a mood tracking entry."""
        entry = MoodEntry(mood="anxious", intensity=7, context="Before meeting")
        assert entry.intensity == 7

    def test_therapy_state_typing(self):
        """Test that TherapyState accepts expected fields."""
        state: TherapyState = {
            "user_id": "user-123",
            "user_message": "I feel anxious today",
            "conversation_history": [],
            "safety_classification": "routine",
            "workflow": "routine",
            "turn_count": 0,
            "needs_consolidation": False,
        }
        assert state["user_id"] == "user-123"
        assert state["safety_classification"] == "routine"


class TestActiveTherapist:
    @pytest.mark.asyncio
    async def test_requests_concise_human_sounding_replies(self):
        from app.services.langgraph_therapy import active_therapist_node

        completion = AsyncMock(return_value="That sounds really hard. Want to tell me what happened?")
        with patch(
            "app.services.langgraph_therapy.groq_client.chat_completion",
            new=completion,
        ):
            result = await active_therapist_node({
                "user_id": "concise-reply-test",
                "user_message": "I'm feeling down about school.",
            })

        prompt = completion.await_args.kwargs["messages"][0]["content"]
        assert "2-4 short sentences" in prompt
        assert "Avoid headings, long bullet lists" in prompt
        assert completion.await_args.kwargs["max_tokens"] == 450
        assert result["ai_response"] == "That sounds really hard. Want to tell me what happened?"


class TestGraphStore:
    """Tests for LangGraph Store helpers."""

    def test_store_singleton(self):
        """Test that get_store returns the same instance."""
        store1 = get_store()
        store2 = get_store()
        assert store1 is store2

    @pytest.mark.asyncio
    async def test_initialize_and_close_postgres_store(self, monkeypatch):
        store = MagicMock()
        store.setup = AsyncMock()
        context = MagicMock()
        context.__aenter__ = AsyncMock(return_value=store)
        context.__aexit__ = AsyncMock(return_value=False)
        from_conn_string = MagicMock(return_value=context)
        monkeypatch.setattr(graph_store, "_store", None)
        monkeypatch.setattr(graph_store, "_store_context", None)
        monkeypatch.setattr(
            graph_store.AsyncPostgresStore,
            "from_conn_string",
            from_conn_string,
        )

        await graph_store.initialize_store()
        assert graph_store.get_store() is store
        store.setup.assert_awaited_once()
        from_conn_string.assert_called_once()

        await graph_store.close_store()
        context.__aexit__.assert_awaited_once_with(None, None, None)
        assert graph_store._store is None

    @pytest.mark.asyncio
    async def test_clinical_profile_upsert_and_get(self):
        """Test writing and reading a clinical profile."""
        user_id = "test-user-profile"
        profile = ClinicalProfile(
            important_context="Lives alone, recently divorced",
            goals="Manage anxiety",
            challenges="Insomnia, work stress",
            support_preferences="Prefers practical advice",
            known_triggers=["crowds", "deadlines"],
        )
        await upsert_clinical_profile(user_id, profile)

        retrieved = await get_clinical_profile(user_id)
        assert retrieved.important_context == "Lives alone, recently divorced"
        assert "crowds" in retrieved.known_triggers

        # Clean up
        await delete_all_memory(user_id)

    @pytest.mark.asyncio
    async def test_distress_events(self):
        """Test adding and retrieving distress events."""
        user_id = "test-user-distress"
        await add_distress_event(
            user_id,
            DistressEvent(severity="high", description="Expressed harm intent"),
        )
        await add_distress_event(
            user_id,
            DistressEvent(severity="low", description="Mild frustration"),
        )

        events = await get_distress_events(user_id)
        assert len(events) >= 2
        severities = [e.severity for e in events]
        assert "high" in severities

        await delete_all_memory(user_id)

    @pytest.mark.asyncio
    async def test_session_summaries(self):
        """Test adding and retrieving session summaries."""
        user_id = "test-user-sessions"
        await add_session_summary(
            user_id,
            SessionSummary(
                session_id="sess-001",
                summary="Discussed work-life balance",
                key_topics=["work", "balance"],
            ),
        )

        summaries = await get_session_summaries(user_id)
        assert len(summaries) >= 1
        assert summaries[0].session_id == "sess-001"

        await delete_all_memory(user_id)

    @pytest.mark.asyncio
    async def test_mood_history(self):
        """Test mood tracking."""
        user_id = "test-user-mood"
        await add_mood_entry(user_id, MoodEntry(mood="happy", intensity=8))
        await add_mood_entry(user_id, MoodEntry(mood="anxious", intensity=6))

        history = await get_mood_history(user_id)
        assert len(history) >= 2

        await delete_all_memory(user_id)

    @pytest.mark.asyncio
    async def test_get_all_memory_blocks(self):
        """Test the bulk memory blocks retrieval."""
        user_id = "test-user-blocks"
        
        await upsert_clinical_profile(
            user_id,
            ClinicalProfile(
                important_context="Test context",
                goals="Test goals",
            ),
        )
        await add_session_summary(
            user_id,
            SessionSummary(session_id="sess-blk", summary="Test summary"),
        )
        await add_mood_entry(user_id, MoodEntry(mood="calm", intensity=7))

        blocks = await get_all_memory_blocks(user_id)
        assert len(blocks) >= 4  # context, goals, session summary, mood

        # Check block structure
        for block in blocks:
            assert "id" in block
            assert "memory_type" in block
            assert "content" in block
        assert any(block["memory_type"].startswith("Mood") for block in blocks)

        await delete_all_memory(user_id)

    @pytest.mark.asyncio
    async def test_delete_all_memory(self):
        """Test that delete_all_memory clears everything."""
        user_id = "test-user-delete"
        await upsert_clinical_profile(user_id, ClinicalProfile(goals="Test"))
        await add_distress_event(user_id, DistressEvent(description="Test"))
        await add_session_summary(
            user_id, SessionSummary(session_id="s1", summary="Test")
        )
        await add_mood_entry(user_id, MoodEntry(mood="ok"))

        await delete_all_memory(user_id)

        assert (await get_clinical_profile(user_id)).goals == ""
        assert len(await get_distress_events(user_id)) == 0
        assert len(await get_session_summaries(user_id)) == 0
        assert len(await get_mood_history(user_id)) == 0


class TestTherapyGraph:
    """Tests for graph structure and routing."""

    def test_graph_compiles(self):
        """Test that the therapy graph compiles without errors."""
        from app.services.langgraph_therapy import get_therapy_graph
        graph = get_therapy_graph()
        assert graph is not None

    def test_graph_has_expected_nodes(self):
        """Test that the graph contains all required agent nodes."""
        from app.services.langgraph_therapy import build_therapy_graph
        graph = build_therapy_graph()
        node_names = set(graph.nodes.keys())
        expected = {
            "load_context",
            "intake_evaluator",
            "active_therapist",
            "emergency_referral",
            "follow_up",
            "professional_referral",
            "safety_review_unavailable",
            "memory_consolidation",
        }
        assert expected.issubset(node_names)

    def test_checkpointer_exists(self):
        """Test that the MemorySaver checkpointer is initialized."""
        from app.services.langgraph_therapy import get_checkpointer
        cp = get_checkpointer()
        assert cp is not None

    @pytest.mark.asyncio
    async def test_initialize_and_close_postgres_checkpointer(self, monkeypatch):
        from app.services import langgraph_therapy

        checkpointer = langgraph_therapy.MemorySaver()
        checkpointer.setup = AsyncMock()
        context = MagicMock()
        context.__aenter__ = AsyncMock(return_value=checkpointer)
        context.__aexit__ = AsyncMock(return_value=False)
        from_conn_string = MagicMock(return_value=context)
        monkeypatch.setattr(langgraph_therapy, "_checkpointer_context", None)
        monkeypatch.setattr(langgraph_therapy, "_compiled_graph", None)
        monkeypatch.setattr(
            langgraph_therapy.AsyncPostgresSaver,
            "from_conn_string",
            from_conn_string,
        )

        await langgraph_therapy.initialize_therapy_graph()
        assert langgraph_therapy.get_checkpointer() is checkpointer
        assert langgraph_therapy.get_therapy_graph() is not None
        checkpointer.setup.assert_awaited_once()

        await langgraph_therapy.close_therapy_graph()
        context.__aexit__.assert_awaited_once_with(None, None, None)
