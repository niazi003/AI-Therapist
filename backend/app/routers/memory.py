"""Memory management API endpoints backed by the LangGraph Store."""
import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_current_user
from app.services.graph_store import get_all_memory_blocks, delete_all_memory
from app.services.langgraph_therapy import get_checkpointer

logger = logging.getLogger(__name__)

router = APIRouter(tags=["memory"])


@router.get("/memory")
async def get_memory_overview(
    current_user: dict = Depends(get_current_user),
):
    """Get user's memory overview as memory blocks from the LangGraph Store."""
    user_id = current_user["user_id"]
    blocks = await get_all_memory_blocks(user_id)
    return blocks


@router.delete("/memory")
async def delete_all_memory_endpoint(
    current_user: dict = Depends(get_current_user),
):
    """Delete all stored memory and short-term conversation state."""
    user_id = current_user["user_id"]
    await delete_all_memory(user_id)
    await get_checkpointer().adelete_thread(f"thread-{user_id}")
    return {"message": "All memory deleted successfully"}


@router.post("/memory/end-conversation")
async def end_current_conversation(
    current_user: dict = Depends(get_current_user),
):
    """End the current conversation while retaining long-term memory."""
    user_id = current_user["user_id"]
    await get_checkpointer().adelete_thread(f"thread-{user_id}")
    return {
        "message": (
            "Conversation ended. Short-term conversation history was cleared; "
            "saved long-term memory remains available."
        )
    }
