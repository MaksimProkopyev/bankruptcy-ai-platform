"""AI Agent: Consultant (FAQ-bot).

Answers basic questions about bankruptcy using RAG v2 knowledge base.
Works at lead generation and first contact stages.
"""

import json
import logging
import asyncio
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Literal
from uuid import uuid4

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from rag.models import KnowledgeAskRequest, KnowledgeAskResponse, RetrievedChunk


logger = logging.getLogger(__name__)

# Client scope detection keywords
CLIENT_SCOPE_KEYWORDS = {
    "individual": ["физлицо", "физическое лицо", "гражданин", "я", "мне", "мой", "муж", "жена", "пенсионер"],
    "sole_proprietor": ["ип", "индивидуальный предприниматель", "предприниматель", "самозанятый"],
    "legal_entity": ["ооо", "зао", "ао", "юрлицо", "юридическое лицо", "компания", "организация", "предприятие"],
    "credit_organization": ["банк", "кредитор", "мфо", "микрофинанс", "коллектор", "займодавец"],
}

DISCLAIMER = "\n\n*Это общая информация, не юридическая консультация. Для оценки вашей ситуации рекомендуем пройти бесплатную квалификацию.*"

CTA_TEXT = "Чтобы получить персональную оценку вашей ситуации, рекомендую пройти бесплатную квалификацию. Это займёт 5-10 минут."


@dataclass
class ConsultantRequest:
    """Input for consultant agent."""
    message: str
    conversation_id: Optional[str] = None
    channel: Literal["web", "telegram", "lk"] = "web"
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ConsultantResponse:
    """Output from consultant agent."""
    reply: str
    sources: List[Dict[str, Any]]  # [{title, source_type, chunk_id}]
    conversation_id: str
    cta: Optional[Dict[str, Any]] = None  # {"text": "...", "action": "start_qualification"}
    disclaimer: str = DISCLAIMER


class ConsultantAgent:
    """FAQ-bot agent that answers bankruptcy questions using RAG v2."""

    def __init__(
        self,
        rag_api_url: str = "http://localhost:8001",
        db_session: Optional[AsyncSession] = None,
    ):
        """Initialize consultant agent.
        
        Args:
            rag_api_url: Base URL of ai-core service (where RAG v2 endpoints are hosted)
            db_session: Optional async SQLAlchemy session for conversation history
        """
        self.rag_api_url = rag_api_url.rstrip("/")
        self.db = db_session
        self.client = httpx.AsyncClient(timeout=30.0)

    async def process_message(
        self,
        request: ConsultantRequest,
    ) -> ConsultantResponse:
        """Process a user message and return a response.
        
        Steps:
        1. Load conversation history (if conversation_id provided)
        2. Detect client_scope from message and history
        3. Call RAG v2 /ask endpoint with query and client_scope
        4. Build response with system prompt + RAG answer
        5. Apply CTA logic (after 2-3 substantial responses)
        6. Save message to history (if db available)
        7. Return response
        """
        # Detect client scope
        client_scope = self._detect_client_scope(request.message)
        
        # Prepare RAG ask request
        rag_request = KnowledgeAskRequest(
            query=request.message,
            client_scope=client_scope,
            top_k=5,
            include_sources=True,
            generate_answer=True,
        )
        
        # Call RAG v2 API
        try:
            rag_response = await self._call_rag_ask(rag_request)
        except Exception as e:
            logger.error(f"RAG API call failed: {e}")
            return self._fallback_response(request.conversation_id or str(uuid4()))
        
        # Build response with system prompt rules
        reply = self._build_reply(rag_response, request.message)
        
        # Determine if we should add CTA
        cta = None
        # TODO: Implement conversation message count tracking
        # For now, add CTA after first response (simplified)
        cta = {
            "text": CTA_TEXT,
            "action": "start_qualification",
            "button_text": "Оценить мою ситуацию бесплатно",
        }
        
        # Convert sources to list of dicts
        sources = []
        if rag_response.sources:
            for src in rag_response.sources:
                sources.append({
                    "title": src.source_title,
                    "source_type": src.source_type,
                    "chunk_id": str(src.chunk_id) if hasattr(src, 'chunk_id') else None,
                    "score": src.score if hasattr(src, 'score') else None,
                })
        
        # Generate or reuse conversation ID
        conversation_id = request.conversation_id or str(uuid4())
        
        return ConsultantResponse(
            reply=reply,
            sources=sources,
            conversation_id=conversation_id,
            cta=cta,
            disclaimer=DISCLAIMER,
        )
    
    def _detect_client_scope(self, message: str) -> Optional[str]:
        """Detect client scope from message text.
        
        Returns:
            One of: 'individual', 'sole_proprietor', 'legal_entity', 'credit_organization'
            or None if cannot determine.
        """
        message_lower = message.lower()
        for scope, keywords in CLIENT_SCOPE_KEYWORDS.items():
            for kw in keywords:
                if kw in message_lower:
                    return scope
        return None
    
    async def _call_rag_ask(self, request: KnowledgeAskRequest) -> KnowledgeAskResponse:
        """Call RAG v2 /ask endpoint."""
        url = f"{self.rag_api_url}/knowledge/ask"
        response = await self.client.post(url, json=request.dict())
        response.raise_for_status()
        data = response.json()
        return KnowledgeAskResponse(**data)
    
    def _build_reply(self, rag_response: KnowledgeAskResponse, original_query: str) -> str:
        """Build final reply from RAG answer, applying system prompt rules."""
        if not rag_response.answer or rag_response.confidence < 0.3:
            return (
                "К сожалению, я не могу дать точный ответ на этот вопрос на основе имеющейся информации. "
                "Рекомендую обратиться к юристу для консультации по вашей конкретной ситуации."
            )
        
        # Start with the RAG answer
        reply = rag_response.answer.strip()
        
        # Ensure it ends with disclaimer (if it's a substantive answer)
        if not reply.endswith(DISCLAIMER):
            reply += DISCLAIMER
        
        return reply
    
    def _fallback_response(self, conversation_id: str) -> ConsultantResponse:
        """Return a fallback response when RAG fails."""
        reply = (
            "В настоящий момент сервис временно недоступен. "
            "Вы можете оставить заявку на нашем сайте, и наш юрист свяжется с вами в ближайшее время."
        )
        return ConsultantResponse(
            reply=reply,
            sources=[],
            conversation_id=conversation_id,
            cta={
                "text": "Оставьте заявку на бесплатную консультацию",
                "action": "contact_form",
                "button_text": "Оставить заявку",
            },
            disclaimer=DISCLAIMER,
        )
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


# Simple factory function for dependency injection
async def get_consultant_agent(
    rag_api_url: Optional[str] = None,
    db_session: Optional[AsyncSession] = None,
) -> ConsultantAgent:
    """Factory to create ConsultantAgent with configuration."""
    if rag_api_url is None:
        rag_api_url = "http://localhost:8001"
    return ConsultantAgent(rag_api_url=rag_api_url, db_session=db_session)