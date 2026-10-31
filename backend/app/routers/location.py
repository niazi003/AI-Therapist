"""Optional IP-based country estimation."""
import ipaddress
import logging

import httpx
from fastapi import APIRouter, HTTPException, Request, status

logger = logging.getLogger(__name__)

router = APIRouter(tags=["location"])
GEOLOCATION_URL = "https://ipwho.is"


def _public_client_ip(
    request: Request,
) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    forwarded_ip = request.headers.get("x-real-ip")
    client_ip = request.client.host if request.client else None

    for candidate in (forwarded_ip, client_ip):
        if not candidate:
            continue
        try:
            address = ipaddress.ip_address(candidate)
        except ValueError:
            continue
        if address.is_global:
            return address
    return None


async def lookup_country_code(
    client_ip: ipaddress.IPv4Address | ipaddress.IPv6Address | None,
) -> str:
    url = f"{GEOLOCATION_URL}/{client_ip}" if client_ip else f"{GEOLOCATION_URL}/"
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(url, headers={"Accept": "application/json"})
        response.raise_for_status()
        data = response.json()

    country_code = data.get("country_code") if isinstance(data, dict) else None
    if (
        not isinstance(data, dict)
        or data.get("success") is not True
        or not isinstance(country_code, str)
        or len(country_code) != 2
        or not country_code.isascii()
        or not country_code.isalpha()
    ):
        raise ValueError("Geolocation provider returned no valid country code")
    return country_code.upper()


@router.get("/location/country")
async def estimate_country(request: Request) -> dict[str, str]:
    """Estimate the caller's country without storing their IP address."""
    try:
        country_code = await lookup_country_code(_public_client_ip(request))
    except (httpx.HTTPError, ValueError) as error:
        logger.warning(
            "Country estimation provider request failed: %s",
            type(error).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Country estimation is temporarily unavailable. You can still share your country in chat.",
        ) from error

    return {"country_code": country_code}
