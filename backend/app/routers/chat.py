"""Chat API endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models.user import User
from app.schemas.user import ChatMessage, ChatResponse
from app.core.security import get_current_user
from app.services.conversation_service import conversation_service
from app.routers.consent import check_user_consent
from app.db import memory_store

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


async def _get_user_id_for_request(
    current_user: dict,
    db: AsyncSession,
) -> str:
    """
    Resolve the user_id for a chat request.

    Falls back to the JWT claim when the database is unavailable so that
    users who authenticated via in-memory mode can still chat.
    """
    user_id = current_user["user_id"]

    try:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            return user.id
        # DB returned nothing — check in-memory store before failing
    except Exception:
        pass  # DB unavailable — fall through to in-memory check

    # Check in-memory store (used when DB is not available)
    mem_user = memory_store.get_user_by_id(user_id)
    if mem_user:
        return mem_user["id"]

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found",
    )


async def _check_consent(user_id: str, db: AsyncSession) -> bool:
    """Check AI processing consent, gracefully handles DB unavailability."""
    try:
        return await check_user_consent(user_id, "ai_processing", db)
    except Exception:
        # If DB is down we can't verify consent — deny to be safe
        return False


@router.post("/chat", response_model=ChatResponse)
async def send_message(
    message: ChatMessage,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a message to the AI companion."""
    user_id = await _get_user_id_for_request(current_user, db)
    has_consent = await _check_consent(user_id, db)

    response = await conversation_service.process_message(
        user_id=user_id,
        message=message.message,
        user_has_consent=has_consent,
        db=db,
        country_code=message.country_code,
    )

    return ChatResponse(
        workflow=response["workflow"],
        message=response["message"],
        clarifying_question=response.get("clarifying_question"),
        urgent_help_info=response.get("urgent_help_info"),
        service_unavailable=response.get("service_unavailable", False),
        support_url=response.get("support_url"),
    )


@router.get("/chat/history")
async def get_chat_history(
    current_user: dict = Depends(get_current_user),
):
    """Get recent chat history from the LangGraph checkpointer."""
    from app.services.langgraph_therapy import get_therapy_graph

    user_id = current_user["user_id"]
    thread_id = f"thread-{user_id}"
    graph = get_therapy_graph()

    try:
        config = {"configurable": {"thread_id": thread_id}}
        state = await graph.aget_state(config)
        if state and state.values:
            history = state.values.get("conversation_history", [])
            messages = [
                {"role": msg["role"], "content": msg["content"]}
                for msg in history
            ]
            return {"messages": messages}
    except Exception as e:
        logger.warning(f"Failed to retrieve history from checkpointer: {e}")

    return {"messages": []}