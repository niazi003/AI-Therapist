"""Tests for server-side crisis helpline lookups."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import settings
from app.tools import koko_helplines


class MockResponse:
    status_code = 200

    def json(self):
        return [
            {
                "name": "Example Crisis Service",
                "displayNumber": "12345",
                "availability": "24/7",
            },
            {"name": "Text Support", "phone": "TEXT"},
            {"phone": "missing name"},
        ]


@pytest.mark.asyncio
async def test_koko_tool_fetches_sanitized_country_resources(monkeypatch):
    request = {}

    class MockClient:
        def __init__(self, timeout):
            assert timeout == 10.0

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_value, traceback):
            return False

        async def get(self, url, *, params, headers):
            request.update(url=url, params=params, headers=headers)
            return MockResponse()

    monkeypatch.setattr(koko_helplines.httpx, "AsyncClient", MockClient)
    monkeypatch.setattr(settings, "KOKO_API_ORIGIN", "https://app.example")
    monkeypatch.setattr(
        settings,
        "KOKO_HELPLINES_API_URL",
        "https://helpline-api.example/crisis_helplines",
    )

    response = await koko_helplines.fetch_koko_helplines.ainvoke({"country": "US"})
    result = json.loads(response)

    assert request["params"] == {"country": "United States"}
    assert request["headers"]["Origin"] == "https://app.example"
    assert request["headers"]["Accept"] == "application/json"
    assert result["status"] == "ok"
    assert result["resources"] == [
        {
            "name": "Example Crisis Service",
            "number": "12345",
            "availability": "24/7",
        },
        {"name": "Text Support", "number": "TEXT"},
    ]


@pytest.mark.asyncio
async def test_koko_tool_does_not_impersonate_vendor_origin(monkeypatch):
    request = {}

    class MockClient:
        def __init__(self, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_value, traceback):
            return False

        async def get(self, url, *, params, headers):
            request["headers"] = headers
            return MockResponse()

    monkeypatch.setattr(koko_helplines.httpx, "AsyncClient", MockClient)
    monkeypatch.setattr(settings, "KOKO_API_ORIGIN", None)
    monkeypatch.setattr(settings, "CORS_ORIGINS", ["http://localhost:5173"])

    await koko_helplines.fetch_koko_helplines.ainvoke({"country": "GB"})

    assert request["headers"]["Origin"] == "http://localhost:5173"
    assert request["headers"]["Origin"] != "https://www.kokocares.org"


@pytest.mark.asyncio
async def test_koko_tool_returns_explicit_fallback_on_http_error(monkeypatch):
    class ForbiddenResponse:
        status_code = 403

    class MockClient:
        def __init__(self, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_value, traceback):
            return False

        async def get(self, url, *, params, headers):
            return ForbiddenResponse()

    monkeypatch.setattr(koko_helplines.httpx, "AsyncClient", MockClient)
    monkeypatch.setattr(settings, "KOKO_API_ORIGIN", "https://app.example")

    response = await koko_helplines.fetch_koko_helplines.ainvoke({"country": "CA"})
    result = json.loads(response)

    assert result["status"] == "unavailable"
    assert result["resources"] == []
    assert "could not be retrieved" in result["message"]


@pytest.mark.asyncio
async def test_crisis_referral_node_uses_live_helplines_when_available():
    from app.services import langgraph_therapy

    with (
        patch(
            "app.services.langgraph_therapy.fetch_koko_helplines",
            new=MagicMock(ainvoke=AsyncMock(return_value=json.dumps({
                "status": "ok",
                "resources": [
                    {"name": "Regional Crisis Service", "number": "12345"}
                ],
            }))),
        ),
        patch(
            "app.services.langgraph_therapy.add_distress_event",
            new=AsyncMock(),
        ),
    ):
        result = await langgraph_therapy.emergency_referral_node({
            "user_id": "koko-test",
            "user_message": "Synthetic urgent test",
            "country_code": "GB",
        })

    assert result["workflow"] == "urgent"
    assert "Regional Crisis Service" in result["ai_response"]
    assert "12345" in result["ai_response"]
    assert "Koko helpline directory" in result["ai_response"]


@pytest.mark.asyncio
async def test_crisis_referral_node_falls_back_without_inventing_numbers():
    from app.services import langgraph_therapy

    with (
        patch(
            "app.services.langgraph_therapy.fetch_koko_helplines",
            new=MagicMock(ainvoke=AsyncMock(return_value=json.dumps({
                "status": "unavailable",
                "resources": [],
            }))),
        ),
        patch(
            "app.services.langgraph_therapy.add_distress_event",
            new=AsyncMock(),
        ),
    ):
        result = await langgraph_therapy.emergency_referral_node({
            "user_id": "koko-fallback-test",
            "user_message": "Synthetic urgent test",
            "country_code": "CA",
        })

    assert "can't display verified local helpline numbers right now" in result["ai_response"]
    assert "Are you in immediate danger right now" in result["ai_response"]
    assert "findahelpline.com/countries/ca" in result["ai_response"]
    assert "findahelpline.com/countries/ca" in result["ai_response"]
    assert "911" not in result["ai_response"]
    assert "988" not in result["ai_response"]


@pytest.mark.asyncio
async def test_safety_review_fallback_does_not_treat_failure_as_a_crisis():
    from app.services import langgraph_therapy

    with patch(
        "app.services.langgraph_therapy._lookup_crisis_helplines",
        new=AsyncMock(),
    ) as lookup, patch(
        "app.services.langgraph_therapy.add_distress_event",
        new=AsyncMock(),
    ) as add_distress_event:
        result = await langgraph_therapy.safety_review_unavailable_node({
            "user_id": "safety-fallback-test",
            "user_message": "I'm getting bullied at school because of acne",
            "country_code": "GB",
        })

    assert result["workflow"] == "review_unavailable"
    assert "temporarily unavailable" in result["ai_response"]
    assert "immediate danger" in result["ai_response"]
    assert "Find A Helpline" not in result["ai_response"]
    assert len(result["conversation_history"]) == 2
    lookup.assert_not_awaited()
    add_distress_event.assert_not_awaited()


@pytest.mark.asyncio
async def test_repeated_safety_fallback_keeps_history_and_responds_briefly():
    from app.services import langgraph_therapy

    lookup = AsyncMock(return_value={"status": "unavailable", "resources": []})
    with patch(
        "app.services.langgraph_therapy._lookup_crisis_helplines",
        new=lookup,
    ):
        first = await langgraph_therapy.safety_review_unavailable_node({
            "user_id": "safety-fallback-repeat-test",
            "user_message": "I'm going to buy a gun.",
            "country_code": "PK",
        })
        second = await langgraph_therapy.safety_review_unavailable_node({
            "user_id": "safety-fallback-repeat-test",
            "user_message": "I talked to someone on the call.",
            "country_code": "PK",
            "conversation_history": first["conversation_history"],
        })

    assert len(first["conversation_history"]) == 2
    assert len(second["conversation_history"]) == 4
    assert "temporarily unavailable" in second["ai_response"]
    assert "Find A Helpline" not in second["ai_response"]
    assert len(second["ai_response"].split()) < 60
    lookup.assert_not_awaited()
