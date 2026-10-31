"""Safety workflow tests for the LangGraph-based conversation service."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.conversation_service import ConversationService
from app.services.langgraph_therapy import (
    _crisis_message,
    get_therapy_graph,
    intake_evaluator_node,
    route_after_intake,
)


class TestConversationService:
    """Tests for conversation service safety workflow."""

    @pytest.mark.asyncio
    async def test_process_message_without_consent(self):
        """Test that messages are rejected without consent."""
        service = ConversationService()

        result = await service.process_message(
            user_id="user-123",
            message="Hello",
            user_has_consent=False,
            db=MagicMock(),
        )

        assert result["workflow"] == "review_unavailable"
        assert "Consent" in result["message"]

    @pytest.mark.asyncio
    async def test_urgent_workflow_provides_crisis_info(self):
        """Test that urgent messages provide crisis resources via LangGraph graph."""
        service = ConversationService()

        # Mock the entire LangGraph graph invocation
        with patch("app.services.conversation_service.get_therapy_graph") as mock_graph:
            mock_compiled = MagicMock()
            mock_compiled.ainvoke = AsyncMock(return_value={
                "workflow": "urgent",
                "ai_response": _crisis_message(None),
                "clarifying_question": None,
            })
            mock_graph.return_value = mock_compiled

            result = await service.process_message(
                user_id="user-123",
                message="I want to hurt myself",
                user_has_consent=True,
                db=MagicMock(),
            )

            assert result["workflow"] == "urgent"
            assert result["urgent_help_info"] is not None

    @pytest.mark.asyncio
    async def test_follow_up_workflow_asks_question(self):
        """Test that follow-up workflow returns a clarifying question."""
        service = ConversationService()

        with patch("app.services.conversation_service.get_therapy_graph") as mock_graph:
            mock_compiled = MagicMock()
            mock_compiled.ainvoke = AsyncMock(return_value={
                "workflow": "follow_up",
                "ai_response": "Can you tell me more?",
                "clarifying_question": "Can you tell me more?",
            })
            mock_graph.return_value = mock_compiled

            result = await service.process_message(
                user_id="user-123",
                message="I'm not feeling right",
                user_has_consent=True,
                db=MagicMock(),
            )

            assert result["workflow"] == "follow_up"
            assert result["clarifying_question"] == "Can you tell me more?"

    @pytest.mark.asyncio
    async def test_routine_workflow_returns_response(self):
        """Test that routine messages get an AI response from the graph."""
        service = ConversationService()

        with patch("app.services.conversation_service.get_therapy_graph") as mock_graph:
            mock_compiled = MagicMock()
            mock_compiled.ainvoke = AsyncMock(return_value={
                "workflow": "routine",
                "ai_response": "Hello! How can I help?",
                "clarifying_question": None,
            })
            mock_graph.return_value = mock_compiled

            result = await service.process_message(
                user_id="user-123",
                message="Hello",
                user_has_consent=True,
                db=MagicMock(),
            )

            assert result["workflow"] == "routine"
            assert result["message"] == "Hello! How can I help?"

            graph_input = mock_compiled.ainvoke.await_args.args[0]
            assert graph_input["service_unavailable"] is False
            assert graph_input["support_url"] is None

    @pytest.mark.asyncio
    async def test_professional_referral_workflow_is_accepted(self):
        service = ConversationService()

        with patch("app.services.conversation_service.get_therapy_graph") as mock_graph:
            mock_compiled = MagicMock()
            mock_compiled.ainvoke = AsyncMock(return_value={
                "workflow": "professional_referral",
                "ai_response": "AI replies are temporarily unavailable.",
                "service_unavailable": True,
                "support_url": "https://findahelpline.com/countries/pk",
            })
            mock_graph.return_value = mock_compiled

            result = await service.process_message(
                user_id="user-123",
                message="I want a therapist",
                user_has_consent=True,
                db=MagicMock(),
            )

        assert result["workflow"] == "professional_referral"
        assert result["message"] == "AI replies are temporarily unavailable."
        assert result["service_unavailable"] is True
        assert result["support_url"] == "https://findahelpline.com/countries/pk"

    @pytest.mark.asyncio
    async def test_confirmed_country_is_forwarded_to_graph(self):
        service = ConversationService()

        with patch("app.services.conversation_service.get_therapy_graph") as mock_graph:
            mock_compiled = MagicMock()
            mock_compiled.ainvoke = AsyncMock(return_value={
                "workflow": "urgent",
                "ai_response": "Local resources.",
            })
            mock_graph.return_value = mock_compiled

            await service.process_message(
                user_id="country-forward-test",
                message="I need help",
                user_has_consent=True,
                db=MagicMock(),
                country_code="ca",
            )

        graph_input = mock_compiled.ainvoke.await_args.args[0]
        assert graph_input["country_code"] == "CA"

    @pytest.mark.asyncio
    async def test_graph_error_returns_unavailable(self):
        """Test that graph errors are handled gracefully."""
        service = ConversationService()

        with patch("app.services.conversation_service.get_therapy_graph") as mock_graph:
            mock_compiled = MagicMock()
            mock_compiled.ainvoke = AsyncMock(side_effect=Exception("Graph crash"))
            mock_graph.return_value = mock_compiled

            result = await service.process_message(
                user_id="user-123",
                message="Hello",
                user_has_consent=True,
                db=MagicMock(),
            )

            assert result["workflow"] == "review_unavailable"
            assert "safety check is temporarily unavailable" in result["message"]
            assert "immediate danger" in result["message"]
            assert "Find A Helpline" not in result["message"]
            assert result["urgent_help_info"] is None


class TestCrisisResources:
    def test_known_country_uses_country_specific_resources(self):
        response = _crisis_message("CA")

        assert "findahelpline.com/countries/ca" in response
        assert "local emergency services" in response
        assert "911" not in response
        assert "988" not in response

    def test_unknown_country_does_not_guess_an_emergency_number(self):
        response = _crisis_message(None)

        assert "local emergency services" in response
        assert "Find A Helpline" in response
        assert "911" not in response
        assert "988" not in response

    def test_unsupported_country_uses_country_neutral_guidance(self):
        response = _crisis_message("XX")

        assert "local emergency services" in response
        assert "https://findahelpline.com/" in response
        assert "/countries/xx" not in response


class TestProfessionalReferral:
    @pytest.mark.asyncio
    async def test_therapist_request_routes_to_referral_workflow(self):
        with patch(
            "app.services.langgraph_therapy.groq_client.chat_completion",
            new=AsyncMock(return_value=(
                '{"workflow":"professional_referral",'
                '"referral_type":"therapist","country_code":null}'
            )),
        ):
            result = await intake_evaluator_node({
                "user_id": "referral-test",
                "user_message": "I want to talk to a therapist",
            })

        assert result["safety_classification"] == "professional_referral"
        assert result["referral_type"] == "therapist"
        assert route_after_intake(result) == "professional_referral"

    @pytest.mark.asyncio
    async def test_persistent_physical_symptoms_route_to_medical_referral(self):
        with patch(
            "app.services.langgraph_therapy.groq_client.chat_completion",
            new=AsyncMock(return_value=(
                '{"workflow":"professional_referral",'
                '"referral_type":"medical","country_code":null}'
            )),
        ):
            result = await intake_evaluator_node({
                "user_id": "medical-referral-test",
                "user_message": "I have been vomiting after meals for a month",
            })

        assert result["referral_type"] == "medical"
        assert route_after_intake(result) == "professional_referral"

    @pytest.mark.asyncio
    async def test_country_is_only_kept_when_supported(self):
        with patch(
            "app.services.langgraph_therapy.groq_client.chat_completion",
            new=AsyncMock(return_value=(
                '{"workflow":"urgent","country_code":"CA"}'
            )),
        ):
            result = await intake_evaluator_node({
                "user_id": "country-test",
                "user_message": "I live in Canada",
            })

        assert result["country_code"] == "CA"

    @pytest.mark.asyncio
    async def test_confirmed_country_is_used_when_model_does_not_return_one(self):
        with patch(
            "app.services.langgraph_therapy.groq_client.chat_completion",
            new=AsyncMock(return_value='{"workflow":"urgent","country_code":null}'),
        ):
            result = await intake_evaluator_node({
                "user_id": "confirmed-country-test",
                "user_message": "I need help",
                "country_code": "NZ",
            })

        assert result["country_code"] == "NZ"

    @pytest.mark.asyncio
    async def test_unsupported_country_code_is_not_used(self):
        with patch(
            "app.services.langgraph_therapy.groq_client.chat_completion",
            new=AsyncMock(return_value=(
                '{"workflow":"urgent","country_code":"XX"}'
            )),
        ):
            result = await intake_evaluator_node({
                "user_id": "unsupported-country-test",
                "user_message": "I am in a country not in the supported list",
            })

        assert result["country_code"] is None

    def test_country_code_is_validated_against_iso_country_list(self):
        from app.services.langgraph_therapy import normalize_country_code

        assert normalize_country_code("gb") == "GB"
        assert normalize_country_code("XX") is None
        assert normalize_country_code("1;") is None

    @pytest.mark.asyncio
    async def test_therapist_referral_uses_agent_with_confirmed_country(self):
        from app.services.langgraph_therapy import professional_referral_node

        with patch(
            "app.services.langgraph_therapy.groq_client.chat_completion",
            new=AsyncMock(side_effect=[
                "New Zealand Ministry of Health — https://health.govt.nz/example — "
                "official health service information.",
                "For support in New Zealand, start with the Ministry of Health "
                "resource or a therapist directory.",
            ]),
        ) as completion:
            result = await professional_referral_node({
                "user_id": "referral-test",
                "user_message": "I need a therapist; I have been depressed",
                "referral_type": "therapist",
                "country_code": "NZ",
                "conversation_history": [
                    {"role": "user", "content": "I have been depressed"}
                ],
            })

        assert "New Zealand" in result["ai_response"]
        search_call, response_call = completion.await_args_list
        search_messages = search_call.kwargs["messages"]
        assert "New Zealand" in search_messages[-1]["content"]
        assert "official and reputable ways to find a therapist" in search_messages[-1]["content"]
        assert "depressed" not in str(search_messages)
        assert search_call.kwargs["tools"] == [{"type": "browser_search"}]
        response_messages = response_call.kwargs["messages"]
        assert "New Zealand (NZ)" in response_messages[0]["content"]
        assert "Do not name or recommend" in response_messages[0]["content"]
        assert "Never use tables" in response_messages[0]["content"]
        assert "https://health.govt.nz/example" in response_messages[-2]["content"]
        assert response_call.kwargs["max_tokens"] == 500
        assert "tools" not in response_call.kwargs
        assert result["workflow"] == "professional_referral"

    @pytest.mark.asyncio
    async def test_medical_referral_uses_agent_and_preserves_response(self):
        from app.services.langgraph_therapy import professional_referral_node

        with patch(
            "app.services.langgraph_therapy.groq_client.chat_completion",
            new=AsyncMock(return_value=(
                "Please arrange an assessment with a qualified healthcare professional."
            )),
        ) as completion:
            result = await professional_referral_node({
                "user_id": "medical-referral-test",
                "user_message": "I have persistent headaches",
                "referral_type": "medical",
            })

        assert "qualified healthcare professional" in result["ai_response"]
        messages = completion.await_args.kwargs["messages"]
        assert "Referral type identified by intake: medical" in messages[-1]["content"]
        assert "not provided" in messages[-1]["content"]

    @pytest.mark.asyncio
    async def test_referral_agent_failure_uses_country_aware_fallback(self):
        from app.services.langgraph_therapy import professional_referral_node

        with patch(
            "app.services.langgraph_therapy.groq_client.chat_completion",
            new=AsyncMock(side_effect=RuntimeError("provider unavailable")),
        ):
            result = await professional_referral_node({
                "user_id": "referral-fallback-test",
                "user_message": "I want a therapist",
                "referral_type": "therapist",
                "country_code": "NZ",
            })

        assert "AI replies are temporarily unavailable" in result["ai_response"]
        assert result["service_unavailable"] is True
        assert result["support_url"] == "https://findahelpline.com/countries/nz"

    @pytest.mark.asyncio
    async def test_combined_referral_failure_exposes_human_support_link(self):
        from app.services.langgraph_therapy import professional_referral_node

        with patch(
            "app.services.langgraph_therapy.groq_client.chat_completion",
            new=AsyncMock(side_effect=RuntimeError("provider unavailable")),
        ):
            result = await professional_referral_node({
                "user_id": "combined-referral-fallback-test",
                "user_message": (
                    "Should I go to a dermatologist to fix my acne or a therapist "
                    "to feel better?"
                ),
                "referral_type": "both",
            })

        assert "AI replies are temporarily unavailable" in result["ai_response"]
        assert result["service_unavailable"] is True
        assert result["support_url"] == "https://findahelpline.com/"

    @pytest.mark.asyncio
    async def test_referral_rate_limit_explains_quota_and_returns_country_link(self):
        import httpx
        from groq import RateLimitError
        from app.services.langgraph_therapy import professional_referral_node

        rate_limit = RateLimitError(
            "daily token limit reached",
            response=httpx.Response(
                429,
                request=httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions"),
            ),
            body={"error": {"code": "rate_limit_exceeded"}},
        )
        with patch(
            "app.services.langgraph_therapy.groq_client.chat_completion",
            new=AsyncMock(side_effect=rate_limit),
        ):
            result = await professional_referral_node({
                "user_id": "referral-rate-limit-test",
                "user_message": "Should I see a dermatologist or therapist?",
                "referral_type": "both",
                "country_code": "PK",
            })

        assert "reached its usage limit" in result["ai_response"]
        assert result["service_unavailable"] is True
        assert result["support_url"] == "https://findahelpline.com/countries/pk"


class TestSafetyReviewScenarios:
    """Verify the intake evaluator routes model output safely."""

    @pytest.mark.asyncio
    async def test_valid_urgent_classification(self):
        with patch(
            "app.services.langgraph_therapy.groq_client.chat_completion",
            new=AsyncMock(return_value='{"workflow":"urgent","reason":"risk"}'),
        ) as completion:
            result = await intake_evaluator_node({
                "user_id": "safety-test",
                "user_message": "I am in immediate danger",
            })

        assert result["safety_classification"] == "urgent"
        assert route_after_intake(result) == "emergency_referral"
        from app.core.config import settings
        assert completion.await_args.kwargs["model"] == settings.GROQ_SAFETY_MODEL
        assert completion.await_args.kwargs["response_format"] == {"type": "json_object"}

    @pytest.mark.asyncio
    async def test_invalid_json_fails_closed(self):
        with patch(
            "app.services.langgraph_therapy.groq_client.chat_completion",
            new=AsyncMock(return_value="I think this is routine."),
        ):
            result = await intake_evaluator_node({
                "user_id": "safety-test",
                "user_message": "Please help",
            })

        assert result["safety_classification"] == "review_unavailable"
        assert route_after_intake(result) == "safety_review_unavailable"

    @pytest.mark.asyncio
    async def test_graph_does_not_run_therapist_if_safety_review_fails(self):
        with patch(
            "app.services.langgraph_therapy.groq_client.chat_completion",
            new=AsyncMock(return_value="invalid response"),
        ) as completion:
            result = await get_therapy_graph().ainvoke(
                {
                    "user_id": "safety-graph-test",
                    "user_message": "Please help",
                },
                config={"configurable": {"thread_id": "safety-graph-test"}},
            )

        assert result["workflow"] == "review_unavailable"
        assert "safety check is temporarily unavailable" in result["ai_response"]
        assert "Find A Helpline" not in result["ai_response"]
        assert "immediate danger" in result["ai_response"]
        assert completion.await_count == 1

    def test_missing_classification_fails_closed(self):
        assert route_after_intake({}) == "safety_review_unavailable"

    @pytest.mark.asyncio
    async def test_safety_model_failure_fails_closed(self):
        with patch(
            "app.services.langgraph_therapy.groq_client.chat_completion",
            new=AsyncMock(side_effect=RuntimeError("provider unavailable")),
        ):
            result = await intake_evaluator_node({
                "user_id": "safety-test",
                "user_message": "Please help",
            })

        assert result["safety_classification"] == "review_unavailable"
        assert route_after_intake(result) == "safety_review_unavailable"

    @pytest.mark.asyncio
    async def test_unknown_workflow_fails_closed(self):
        with patch(
            "app.services.langgraph_therapy.groq_client.chat_completion",
            new=AsyncMock(return_value='{"workflow":"unknown"}'),
        ):
            result = await intake_evaluator_node({
                "user_id": "safety-test",
                "user_message": "Please help",
            })

        assert result["safety_classification"] == "review_unavailable"