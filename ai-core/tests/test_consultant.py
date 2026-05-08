"""Unit tests for ConsultantAgent."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from ai_core.agents.consultant import (
    ConsultantAgent,
    ConsultantRequest,
    ConsultantResponse,
    CLIENT_SCOPE_KEYWORDS,
)


@pytest.fixture
def mock_rag_response():
    """Mock RAG response."""
    return {
        "answer": "Судебное банкротство стоит 250 000 ₽, внесудебное — 35 000 ₽.",
        "sources": [
            {
                "chunk_id": str(uuid4()),
                "source_title": "Закон о банкротстве",
                "source_type": "law",
                "score": 0.9,
            }
        ],
        "confidence": 0.8,
        "query_id": str(uuid4()),
        "timing": {"retrieval": 100, "generation": 500},
    }


@pytest.fixture
def agent():
    """Create ConsultantAgent with mocked HTTP client."""
    with patch("ai_core.agents.consultant.httpx.AsyncClient") as mock_client:
        mock_client.return_value = AsyncMock()
        agent = ConsultantAgent(rag_api_url="http://mock")
        agent.client = mock_client.return_value
        yield agent


@pytest.mark.asyncio
async def test_detect_client_scope(agent):
    """Test client scope detection from message."""
    # Individual
    assert agent._detect_client_scope("Я гражданин") == "individual"
    assert agent._detect_client_scope("мне нужна помощь") == "individual"
    # Sole proprietor
    assert agent._detect_client_scope("Я ИП") == "sole_proprietor"
    assert agent._detect_client_scope("индивидуальный предприниматель") == "sole_proprietor"
    # Legal entity
    assert agent._detect_client_scope("Наше ООО") == "legal_entity"
    # Credit organization
    assert agent._detect_client_scope("Банк требует") == "credit_organization"
    # No match
    assert agent._detect_client_scope("Сколько стоит?") is None


@pytest.mark.asyncio
async def test_process_message_success(agent, mock_rag_response):
    """Test successful message processing."""
    # Mock RAG API call
    agent.client.post = AsyncMock(return_value=MagicMock(
        raise_for_status=MagicMock(),
        json=MagicMock(return_value=mock_rag_response)
    ))
    
    request = ConsultantRequest(
        message="Сколько стоит банкротство?",
        channel="web",
    )
    
    response = await agent.process_message(request)
    
    assert isinstance(response, ConsultantResponse)
    assert response.reply
    assert "250 000" in response.reply or "банкротство" in response.reply
    assert response.disclaimer
    assert response.conversation_id
    # CTA should be present (simplified logic)
    assert response.cta is not None
    assert response.sources


@pytest.mark.asyncio
async def test_process_message_rag_failure(agent):
    """Test fallback when RAG API fails."""
    agent.client.post = AsyncMock(side_effect=Exception("API error"))
    
    request = ConsultantRequest(
        message="Сколько стоит?",
        channel="web",
    )
    
    response = await agent.process_message(request)
    
    assert "недоступен" in response.reply or "ошибка" in response.reply.lower()
    assert response.cta is not None


@pytest.mark.asyncio
async def test_build_reply_high_confidence(agent):
    """Test building reply from high-confidence RAG answer."""
    from rag.models import KnowledgeAskResponse, Citation
    from uuid import uuid4
    
    citations = [
        Citation(
            chunk_id=uuid4(),
            source_id=uuid4(),
            source_title="Закон о банкротстве",
            source_type="law",
            chunk_text="...",
            score=0.9,
        )
    ]
    rag_response = KnowledgeAskResponse(
        answer="Ответ на вопрос.",
        citations=citations,
        confidence=0.9,
        sources_used=["law"],
        query_id=uuid4(),
        timing={},
    )
    
    reply = agent._build_reply(rag_response, "Вопрос")
    assert "Ответ на вопрос." in reply
    assert "Это общая информация" in reply


@pytest.mark.asyncio
async def test_build_reply_low_confidence(agent):
    """Test building reply when confidence is low."""
    from rag.models import KnowledgeAskResponse, Citation
    from uuid import uuid4
    
    citations = [
        Citation(
            chunk_id=uuid4(),
            source_id=uuid4(),
            source_title="Закон",
            source_type="law",
            chunk_text="...",
            score=0.1,
        )
    ]
    rag_response = KnowledgeAskResponse(
        answer="Не уверен.",
        citations=citations,
        confidence=0.2,
        sources_used=["law"],
        query_id=uuid4(),
        timing={},
    )
    
    reply = agent._build_reply(rag_response, "Вопрос")
    assert "не могу дать точный ответ" in reply or "юристу" in reply


def test_fallback_response(agent):
    """Test fallback response generation."""
    conv_id = str(uuid4())
    response = agent._fallback_response(conv_id)
    assert response.conversation_id == conv_id
    assert "недоступен" in response.reply or "ошибка" in response.reply.lower()
    assert response.cta is not None


@pytest.mark.asyncio
async def test_close(agent):
    """Test closing HTTP client."""
    agent.client.aclose = AsyncMock()
    await agent.close()
    agent.client.aclose.assert_called_once()