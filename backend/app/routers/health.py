"""Health check API endpoint."""
import logging

from fastapi import APIRouter
from sqlalchemy import text

from app.schemas.user import HealthResponse
from app.core.config import settings
from app.services.groq_client import groq_client
from app.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check application health and service status."""
    # Check Groq
    groq_status = "configured" if groq_client.is_configured() else "not_configured"

    # Check LangGraph (always available — it's in-process)
    langgraph_status = "available"
    try:
        from app.services.langgraph_therapy import get_therapy_graph
        graph = get_therapy_graph()
        if graph is None:
            langgraph_status = "error"
    except Exception:
        langgraph_status = "error"

    # Check database connectivity
    db_status = "unavailable"
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            db_status = "connected"
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        db_status = "unavailable"

    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        services={
            "groq": groq_status,
            "langgraph": langgraph_status,
            "database": db_status,
        },
    )