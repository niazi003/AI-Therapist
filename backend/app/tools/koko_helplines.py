"""Server-side Koko crisis helpline lookup."""
from __future__ import annotations

import json
import logging
from typing import Any
from urllib.parse import urlparse

import httpx
import pycountry
from langchain_core.tools import tool

from app.core.config import settings

logger = logging.getLogger(__name__)

def _country_name(country: str) -> str | None:
    value = country.strip()
    if not value:
        return None

    for candidate in pycountry.countries:
        for field in ("alpha_2", "alpha_3", "name", "official_name", "common_name"):
            if getattr(candidate, field, "").casefold() == value.casefold():
                return candidate.name
    return None


def _resource_payload(payload: Any) -> list[dict[str, str]]:
    if not isinstance(payload, list):
        raise ValueError("Koko returned an invalid helpline response")

    resources = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        number = (
            item.get("displayNumber")
            or item.get("formattedCallNumber")
            or item.get("phone")
        )
        if not isinstance(name, str) or not name.strip():
            continue
        if not isinstance(number, str) or not number.strip():
            continue

        resource = {"name": name.strip()[:160], "number": number.strip()[:80]}
        availability = item.get("availability")
        if isinstance(availability, str) and availability.strip():
            resource["availability"] = availability.strip()[:80]
        resources.append(resource)
        if len(resources) == 8:
            break
    return resources


async def _fetch_koko_helplines(country: str) -> dict[str, Any]:
    country_name = _country_name(country)
    if not country_name:
        return {
            "status": "invalid_country",
            "resources": [],
            "message": "A valid country name or ISO country code is required.",
        }

    app_origin = settings.KOKO_API_ORIGIN or (
        settings.CORS_ORIGINS[0] if settings.CORS_ORIGINS else ""
    )
    parsed_origin = urlparse(app_origin)
    if parsed_origin.scheme not in ("http", "https") or not parsed_origin.netloc:
        logger.error("Koko lookup skipped because the application Origin is not configured")
        return {
            "status": "unavailable",
            "country": country_name,
            "resources": [],
            "message": "The crisis helpline service is not configured for this application.",
        }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                settings.KOKO_HELPLINES_API_URL,
                params={"country": country_name},
                headers={
                    "Accept": "application/json",
                    "Origin": app_origin,
                },
            )
        if response.status_code != 200:
            logger.warning(
                "Koko helplines lookup returned HTTP %s for country %s",
                response.status_code,
                country_name,
            )
            return {
                "status": "unavailable",
                "country": country_name,
                "resources": [],
                "message": "Current local crisis helplines could not be retrieved.",
            }

        resources = _resource_payload(response.json())
        return {
            "status": "ok" if resources else "empty",
            "country": country_name,
            "resources": resources,
            "message": (
                "Current crisis helplines retrieved."
                if resources
                else "No crisis helplines were returned for this country."
            ),
        }
    except (httpx.TimeoutException, httpx.RequestError, ValueError) as error:
        logger.warning(
            "Koko helplines lookup failed for country %s: %s",
            country_name,
            type(error).__name__,
        )
        return {
            "status": "unavailable",
            "country": country_name,
            "resources": [],
            "message": "Current local crisis helplines could not be retrieved.",
        }


@tool("fetch_koko_helplines")
async def fetch_koko_helplines(country: str) -> str:
    """Fetch current crisis helplines for a country from Koko's directory.

    Pass an ISO 3166-1 alpha-2/alpha-3 code or country name. The request runs
    server-side and identifies this application with its configured CORS origin.
    """
    return json.dumps(await _fetch_koko_helplines(country), ensure_ascii=False)
