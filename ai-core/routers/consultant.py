"""FastAPI router for Consultant Agent (FAQ-bot)."""

import logging
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from agents.consultant import (
    ConsultantAgent,
    ConsultantRequest,
    ConsultantResponse,
    get_consultant_agent,
)
from database import get_db  # Assuming there's a db session dependency

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["consultant"])


# Pydantic schemas for API
class ConsultantMessageRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    channel: str = "web"  # web, telegram, lk
    metadata: Optional[dict] = None


class ConsultantMessageResponse(BaseModel):
    reply: str
    sources: list[dict]
    conversation_id: str
    cta: Optional[dict] = None
    disclaimer: str


@router.post("/consultant", response_model=ConsultantMessageResponse)
async def chat_with_consultant(
    request: ConsultantMessageRequest,
    agent: ConsultantAgent = Depends(get_consultant_agent),
    db: AsyncSession = Depends(get_db),
):
    """Chat endpoint for consultant FAQ-bot.
    
    Processes user message, retrieves answer from RAG v2 knowledge base,
    and returns response with sources and optional CTA.
    """
    try:
        # Convert to agent request
        agent_request = ConsultantRequest(
            message=request.message,
            conversation_id=request.conversation_id,
            channel=request.channel,  # type: ignore
            metadata=request.metadata,
        )
        
        # Process through agent
        response = await agent.process_message(agent_request)
        
        # Convert to API response
        return ConsultantMessageResponse(
            reply=response.reply,
            sources=response.sources,
            conversation_id=response.conversation_id,
            cta=response.cta,
            disclaimer=response.disclaimer,
        )
    except Exception as e:
        logger.exception(f"Consultant agent error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/consultant/{conversation_id}/history")
async def get_conversation_history(
    conversation_id: str,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve conversation history.
    
    TODO: Implement when ai_conversations and ai_messages tables exist.
    """
    # Placeholder response
    return {
        "conversation_id": conversation_id,
        "messages": [],
        "total": 0,
        "note": "History storage not yet implemented",
    }