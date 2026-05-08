
"""AI Core Service — orchestrates all AI agents.

Runs as a separate service on port 8001.
Backend communicates with this service via HTTP API.
"""

import os
import time
import json
import hashlib
import logging
from uuid import uuid4
from typing import Optional, List, Dict, Any

import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# RAG v2 imports
from rag.config import RAGConfig
from rag.models import (
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeAskRequest,
    KnowledgeAskResponse,
    SourceCreateRequest,
    SourceResponse,
    FeedbackRequest,
    KnowledgeStatsResponse,
    RetrievedChunk,
)
from rag.ingestion.embedder import EmbeddingService
from rag.ingestion.pipeline import IngestionPipeline
from rag.retrieval.query_processor import QueryProcessor
from rag.retrieval.vector_search import VectorSearch
from rag.retrieval.fts_search import FTSSearch
from rag.retrieval.hybrid import HybridRetriever
from rag.retrieval.reranker import ClaudeReranker
from rag.generation.context_builder import ContextBuilder
from rag.generation.generator import RAGGenerator
from ai_core.routers.consultant import router as consultant_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Bankruptcy AI Core", version="0.2.0")

# ---- Database setup (async PostgreSQL) ----
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@postgres:5432/bankruptcy"
)
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    """Dependency for async DB session."""
    async with async_session() as session:
        yield session

# ---- Redis client (lazy initialization) ----
_redis_client = None

async def get_redis():
    """Get Redis client (singleton)."""
    global _redis_client
    if _redis_client is None:
        redis_url = "redis://redis:6379"
        _redis_client = redis.from_url(redis_url, decode_responses=True)
    return _redis_client

# ---- RAG v2 components (singletons) ----
config = RAGConfig()
embedder = EmbeddingService(
    api_key=config.openai_api_key,
    model=config.embedding_model,
    batch_size=config.embedding_batch_size,
)
query_processor = QueryProcessor()
context_builder = ContextBuilder(max_context_tokens=config.max_context_tokens)
reranker = ClaudeReranker(api_key=config.anthropic_api_key)
generator = RAGGenerator(api_key=config.anthropic_api_key)

# Include consultant router
app.include_router(consultant_router, prefix="/api/v1/chat", tags=["consultant"])

# ---- Schemas (existing) ----

class QualificationRequest(BaseModel):
    total_debt: float
    creditors_count: int
    creditor_types: list[str]
    monthly_income: float | None = None
    is_employed: bool = False
    has_property: bool = False
    property_types: list[str] = []
    has_transactions_3y: bool = False
    marital_status: str = "single"
    has_enforcement_proceedings: bool = False
    region: str | None = None


class QualificationResponse(BaseModel):
    is_eligible: bool
    recommended_procedure: str
    procedure_type: str | None
    estimated_cost_min: float
    estimated_cost_max: float
    estimated_duration_months_min: int
    estimated_duration_months_max: int
    risk_level: str
    risk_factors: list[str]
    confidence: float
    explanation: str
    needs_lawyer_review: bool
    score: int = 0
    tier: str = "cold"
    sla_hours: int = 24
    briefing_card: dict = {}


class OCRRequest(BaseModel):
    file_path: str
    document_type_hint: str | None = None


class OCRResponse(BaseModel):
    detected_type: str
    confidence: float
    extracted_text: str
    structured_data: dict
    processing_time_ms: int


class DocumentGenRequest(BaseModel):
    template: str  # bankruptcy_application, creditors_registry, etc.
    case_data: dict
    client_data: dict
    creditors_data: list[dict] = []


class DocumentGenResponse(BaseModel):
    file_path: str
    file_name: str
    warnings: list[str] = []
    processing_time_ms: int


class ChatMessage(BaseModel):
    role: str  # user, assistant
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    session_id: str | None = None
    context: dict = {}  # case_id, client_id, etc.


class ChatResponse(BaseModel):
    reply: str
    action: str | None = None  # qualify, schedule, escalate
    action_data: dict | None = None
    session_id: str


# ---- Existing endpoints (unchanged) ----

@app.get("/health")
async def health():
    return {"status": "ok", "service": "ai-core"}


@app.post("/qualify", response_model=QualificationResponse)
async def qualify_lead(req: QualificationRequest):
    """Run AI qualification scoring."""
    from agents.qualification import QualificationAgent, QualificationInput, pre_screen, calculate_score

    start = time.time()

    # Generate cache key from input data
    input_json = json.dumps(req.model_dump(mode="json"), sort_keys=True)
    cache_key = f"qualify:{hashlib.sha256(input_json.encode()).hexdigest()}"

    # Try to get cached result (including pre-screen failures)
    redis_client = await get_redis()
    cached = await redis_client.get(cache_key)
    if cached:
        cached_data = json.loads(cached)
        cached_data["cached"] = True
        return QualificationResponse(**cached_data)

    # Step 1: Rule-based pre-screen
    input_data = QualificationInput(
        total_debt=req.total_debt,
        creditors_count=req.creditors_count,
        creditor_types=req.creditor_types,
        monthly_income=req.monthly_income,
        is_employed=req.is_employed,
        has_property=req.has_property,
        property_types=req.property_types,
        has_transactions_3y=req.has_transactions_3y,
        marital_status=req.marital_status,
        has_enforcement_proceedings=req.has_enforcement_proceedings,
        region=req.region,
    )

    pre = pre_screen(input_data)
    if not pre["pass"]:
        # Cache pre-screen failure as well
        response_data = {
            "is_eligible": False,
            "recommended_procedure": "not_eligible",
            "procedure_type": None,
            "estimated_cost_min": 0,
            "estimated_cost_max": 0,
            "estimated_duration_months_min": 0,
            "estimated_duration_months_max": 0,
            "risk_level": "low",
            "risk_factors": [],
            "confidence": 0.95,
            "explanation": pre["reason"],
            "needs_lawyer_review": False,
            "score": 0,
            "tier": "disqualified",
            "sla_hours": 0,
            "briefing_card": {"recommended_action": "Отказ — клиент не соответствует критериям"},
        }
        await redis_client.setex(cache_key, 86400, json.dumps(response_data))
        return QualificationResponse(**response_data)

    # Step 2: LLM scoring with fallback
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")
    gigachat_key = os.environ.get("GIGACHAT_API_KEY")
    yandex_api_key = os.environ.get("YANDEX_API_KEY")
    yandex_folder_id = os.environ.get("YANDEX_FOLDER_ID")
    ollama_base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")

    # Check if any LLM provider is configured
    any_llm_configured = any([anthropic_key, openai_key, gigachat_key, yandex_api_key, ollama_base_url])
    if not any_llm_configured:
        # No API keys, return rule-based fallback (already cached)
        response_data = {
            "is_eligible": True,
            "recommended_procedure": "judicial",
            "procedure_type": "asset_realization",
            "estimated_cost_min": 80000,
            "estimated_cost_max": 150000,
            "estimated_duration_months_min": 8,
            "estimated_duration_months_max": 12,
            "risk_level": "medium",
            "risk_factors": pre.get("flags", []),
            "confidence": 0.6,
            "explanation": "AI-модели не настроены. Предварительная оценка на основе правил.",
            "needs_lawyer_review": True,
            "score": 0,
            "tier": "cold",
            "sla_hours": 24,
            "briefing_card": {},
        }
        await redis_client.setex(cache_key, 86400, json.dumps(response_data))
        return QualificationResponse(**response_data)

    agent = QualificationAgent(
        anthropic_api_key=anthropic_key,
        openai_api_key=openai_key,
        gigachat_api_key=gigachat_key,
        yandex_api_key=yandex_api_key,
        yandex_folder_id=yandex_folder_id,
        ollama_base_url=ollama_base_url,
    )
    result = await agent.qualify(input_data)

    # Calculate score and routing
    qs = calculate_score(result, input_data)

    # Prepare response data
    response_data = {
        "is_eligible": result.is_eligible,
        "recommended_procedure": result.recommended_procedure,
        "procedure_type": result.procedure_type,
        "estimated_cost_min": result.estimated_cost_min,
        "estimated_cost_max": result.estimated_cost_max,
        "estimated_duration_months_min": result.estimated_duration_months_min,
        "estimated_duration_months_max": result.estimated_duration_months_max,
        "risk_level": result.risk_level,
        "risk_factors": result.risk_factors,
        "confidence": result.confidence,
        "explanation": result.explanation,
        "needs_lawyer_review": result.needs_lawyer_review,
        "score": qs.score,
        "tier": qs.tier,
        "sla_hours": qs.sla_hours,
        "briefing_card": qs.briefing_card,
    }

    # Cache for 24 hours (86400 seconds)
    await redis_client.setex(cache_key, 86400, json.dumps(response_data))

    elapsed_ms = int((time.time() - start) * 1000)

    return QualificationResponse(**response_data)


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Conversational AI — qualification chatbot and client assistant."""
    import os
    import anthropic
    from prompts.chatbot_qualification import CHATBOT_SYSTEM_PROMPT

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=503, detail="ANTHROPIC_API_KEY not configured")

    client = anthropic.Anthropic(api_key=api_key)
    session_id = req.session_id or str(uuid4())

    messages = [{"role": m.role, "content": m.content} for m in req.messages]

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        system=CHATBOT_SYSTEM_PROMPT,
        messages=messages,
    )

    reply_text = response.content[0].text

    # Check if the bot returned a JSON action (qualification complete)
    action = None
    action_data = None

    if '{"action"' in reply_text:
        try:
            # Try to extract JSON from the response
            json_start = reply_text.index("{")
            json_str = reply_text[json_start:]
            parsed = json.loads(json_str)
            if parsed.get("action") == "qualify":
                action = "qualify"
                action_data = parsed.get("data", {})
                reply_text = reply_text[:json_start].strip()
                if not reply_text:
                    reply_text = "Спасибо! Подготовлю предварительную оценку..."
        except (json.JSONDecodeError, ValueError):
            pass

    return ChatResponse(
        reply=reply_text,
        action=action,
        action_data=action_data,
        session_id=session_id,
    )


@app.post("/ocr", response_model=OCRResponse)
async def process_document(req: OCRRequest):
    """OCR + data extraction from uploaded document."""
    import time
    from ocr.engine import get_ocr_engine
    from agents.ocr_extraction import OCRAgent

    start = time.time()

    # 1. OCR
    engine = get_ocr_engine()
    try:
        ocr_text = engine.extract_text(req.file_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR failed: {str(e)}")

    # 2. Classification & extraction
    agent = OCRAgent()
    try:
        result = await agent.process_document(ocr_text, req.document_type_hint)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")

    elapsed_ms = int((time.time() - start) * 1000)

    return OCRResponse(
        detected_type=result["document_type"],
        confidence=result["confidence"],
        extracted_text=ocr_text[:5000],  # limit for response
        structured_data=result["extracted_data"],
        processing_time_ms=elapsed_ms,
    )


@app.post("/generate-document", response_model=DocumentGenResponse)
async def generate_document(req: DocumentGenRequest):
    """Generate legal document from template + case data."""
    # TODO: implement document generation
    raise HTTPException(status_code=501, detail="Document generation not implemented yet")


# ---- Legacy RAG v1 endpoints (keep for compatibility) ----

@app.post("/rag/search")
async def rag_search(query: str, top_k: int = 5, source_type: str | None = None):
    """Search knowledge base (laws, court decisions, templates)."""
    return {
        "query": query,
        "top_k": top_k,
        "source_type": source_type,
        "results": [],
        "message": "RAG search available after running: POST /rag/index-seed",
    }


@app.post("/rag/answer")
async def rag_answer(query: str, top_k: int = 5):
    """Answer legal question using knowledge base context + LLM."""
    return {
        "query": query,
        "answer": "RAG answer available after knowledge base indexing",
        "sources": [],
    }


@app.post("/rag/index-seed")
async def rag_index_seed():
    """Index seed legal data (key articles from ФЗ-127) into knowledge base."""
    from rag.pipeline import FZ127_KEY_ARTICLES
    indexed = 0
    for article in FZ127_KEY_ARTICLES:
        indexed += 1
    return {
        "indexed_articles": indexed,
        "message": f"Indexed {indexed} articles from ФЗ-127. Full indexing requires PostgreSQL+pgvector connection.",
    }


# ---- RAG v2 endpoints (new) ----

@app.post("/knowledge/search", response_model=KnowledgeSearchResponse)
async def knowledge_search(
    request: KnowledgeSearchRequest,
    db: AsyncSession = Depends(get_db),
):
    """Hybrid search across knowledge base."""
    start = time.time()

    try:
        # 1. Process query
        processed = query_processor.process(request.query)
        # 2. Embed query
        embedding = await embedder.embed_query(processed.normalized_query)
        # 3. Hybrid retrieval
        retriever = HybridRetriever(db)
        results = await retriever.search(
            query=request.query,
            embedding=embedding,
            top_k=request.top_k or config.top_k,
            filters=request.filters,
        )
        # 4. Format response
        retrieved = [
            RetrievedChunk(
                chunk_id=r["chunk_id"],
                source_id=r["source_id"],
                source_type=r["source_type"],
                source_title=r["source_title"],
                chunk_text=r["chunk_text"],
                chunk_index=r["chunk_index"],
                token_count=r["token_count"],
                metadata=r["metadata"],
                score=r["score"],
            )
            for r in results
        ]
        query_time_ms = int((time.time() - start) * 1000)

        return KnowledgeSearchResponse(
            results=retrieved,
            total=len(retrieved),
            query_time_ms=query_time_ms,
        )
    except Exception as e:
        logger.exception("Search failed")
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


@app.post("/knowledge/ask", response_model=KnowledgeAskResponse)
async def knowledge_ask(
    request: KnowledgeAskRequest,
    db: AsyncSession = Depends(get_db),
):
    """Question‑answering with RAG."""
    start = time.time()

    try:
        # 1. Process query with case context
        processed = await query_processor.process(
            request.query,
            case_context=str(request.case_id) if request.case_id else None,
        )
        # 2. Embed query
        embedding = await embedder.embed_query(processed.normalized_query)
        # 3. Hybrid retrieval
        retriever = HybridRetriever(db)
        candidates = await retriever.search(
            query=request.query,
            embedding=embedding,
            filters=request.filters,
        )
        # 4. Rerank
        top_chunks = await reranker.rerank(
            query=request.query,
            candidates=candidates,
            top_n=config.rerank_top_n,
        )
        # 5. Build context
        context = context_builder.build(top_chunks, include_metadata=True)
        # 6. Generate answer
        generation_result = await generator.generate(
            query=request.query,
            context=context,
            chunks=top_chunks,
            source=request.source or "lawyer",
        )
        # 7. Prepare timings
        total_time_ms = int((time.time() - start) * 1000)
        # 8. Save query asynchronously (fire‑and‑forget)
        # (In a real implementation
        # (In a real implementation we would insert into rag_queries table)
        query_id = str(uuid4())

        # 9. Build response
        return KnowledgeAskResponse(
            answer=generation_result["answer"],
            citations=generation_result["citations"],
            confidence=generation_result["confidence"],
            sources_used=[c["source_title"] for c in top_chunks[:3]],
            query_id=query_id,
            timing={
                "total_ms": total_time_ms,
                "embedding_ms": 0,  # could be tracked separately
                "retrieval_ms": 0,
                "rerank_ms": 0,
                "generation_ms": 0,
            },
        )
    except Exception as e:
        logger.exception("RAG ask failed")
        raise HTTPException(status_code=500, detail=f"RAG error: {str(e)}")


@app.get("/knowledge/sources")
async def list_sources(
    db: AsyncSession = Depends(get_db),
    source_type: str | None = None,
    limit: int = 100,
    offset: int = 0,
):
    """List knowledge sources."""
    from sqlalchemy import select
    from sqlalchemy.sql import func
    from rag.models import KnowledgeSource

    try:
        query = select(KnowledgeSource)
        if source_type:
            query = query.where(KnowledgeSource.source_type == source_type)
        query = query.limit(limit).offset(offset).order_by(KnowledgeSource.created_at.desc())

        result = await db.execute(query)
        sources = result.scalars().all()

        # Get total count
        count_query = select(func.count(KnowledgeSource.id))
        if source_type:
            count_query = count_query.where(KnowledgeSource.source_type == source_type)
        total = (await db.execute(count_query)).scalar()

        return {
            "sources": [
                {
                    "id": s.id,
                    "source_type": s.source_type,
                    "title": s.title,
                    "description": s.description,
                    "chunks_count": s.chunks_count,
                    "ingestion_status": s.ingestion_status,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                }
                for s in sources
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        logger.exception("Failed to list sources")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.post("/knowledge/sources", response_model=SourceResponse)
async def create_source(
    request: SourceCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Add a new knowledge source."""
    from sqlalchemy.dialects.postgresql import UUID
    from rag.models import KnowledgeSource

    try:
        source = KnowledgeSource(
            source_type=request.source_type,
            title=request.title,
            description=request.description,
            content=request.content,
            external_url=request.external_url,
            file_path=request.file_path,
            tags=request.tags,
            metadata=request.metadata,
            auto_ingest=request.auto_ingest,
            ingestion_status="pending",
        )
        db.add(source)
        await db.commit()
        await db.refresh(source)

        # If auto_ingest and content provided, trigger ingestion asynchronously
        if request.auto_ingest and request.content:
            # In production we would enqueue a background task
            logger.info(f"Source {source.id} queued for ingestion")

        return SourceResponse(
            source_id=source.id,
            status=source.ingestion_status,
            chunks_count=source.chunks_count,
        )
    except Exception as e:
        await db.rollback()
        logger.exception("Failed to create source")
        raise HTTPException(status_code=500, detail=f"Creation error: {str(e)}")


@app.post("/knowledge/sources/{source_id}/ingest")
async def ingest_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Trigger ingestion for an existing source."""
    from sqlalchemy import select
    from rag.models import KnowledgeSource
    from rag.ingestion.pipeline import IngestionPipeline

    try:
        result = await db.execute(select(KnowledgeSource).where(KnowledgeSource.id == source_id))
        source = result.scalar_one_or_none()
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        # Update status
        source.ingestion_status = "processing"
        source.ingestion_started_at = func.now()
        await db.commit()

        # Run ingestion (in production this would be a background job)
        pipeline = IngestionPipeline(db)
        await pipeline.ingest(source)

        source.ingestion_status = "completed"
        source.ingestion_completed_at = func.now()
        await db.commit()

        return {"status": "completed", "chunks_created": source.chunks_count}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Ingestion failed for source {source_id}")
        raise HTTPException(status_code=500, detail=f"Ingestion error: {str(e)}")


@app.delete("/knowledge/sources/{source_id}")
async def delete_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a knowledge source and its chunks."""
    from sqlalchemy import select, delete
    from rag.models import KnowledgeSource, KnowledgeChunk

    try:
        # Check existence
        result = await db.execute(select(KnowledgeSource).where(KnowledgeSource.id == source_id))
        source = result.scalar_one_or_none()
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        # Delete chunks (CASCADE should handle this, but explicit is fine)
        await db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.source_id == source_id))
        await db.execute(delete(KnowledgeSource).where(KnowledgeSource.id == source_id))
        await db.commit()

        return {"deleted": True, "source_id": source_id}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception(f"Failed to delete source {source_id}")
        raise HTTPException(status_code=500, detail=f"Deletion error: {str(e)}")


@app.post("/knowledge/feedback")
async def submit_feedback(request: FeedbackRequest, db: AsyncSession = Depends(get_db)):
    """Submit relevance feedback for a retrieved chunk."""
    from sqlalchemy import select, update
    from rag.models import RAGFeedback, KnowledgeChunk

    try:
        # Insert feedback
        feedback = RAGFeedback(
            query_id=request.query_id,
            chunk_id=request.chunk_id,
            relevance_score=request.relevance_score,
            is_helpful=request.is_helpful,
            comment=request.comment,
            created_by=request.user_id,  # would come from auth
        )
        db.add(feedback)
        await db.commit()

        # Update chunk aggregate stats (optional)
        # This could be done asynchronously
        await db.execute(
            update(KnowledgeChunk)
            .where(KnowledgeChunk.id == request.chunk_id)
            .values(
                feedback_count=KnowledgeChunk.feedback_count + 1,
                avg_relevance_score=(
                    (KnowledgeChunk.avg_relevance_score * KnowledgeChunk.feedback_count + request.relevance_score)
                    / (KnowledgeChunk.feedback_count + 1)
                ),
            )
        )
        await db.commit()

        return {"status": "recorded", "feedback_id": feedback.id}
    except Exception as e:
        await db.rollback()
        logger.exception("Feedback submission failed")
        raise HTTPException(status_code=500, detail=f"Feedback error: {str(e)}")


@app.get("/knowledge/stats", response_model=KnowledgeStatsResponse)
async def knowledge_stats(db: AsyncSession = Depends(get_db)):
    """Get RAG system statistics."""
    from sqlalchemy import select, func, text
    from rag.models import KnowledgeSource, KnowledgeChunk, RAGQuery, RAGFeedback

    try:
        # Total sources and chunks
        total_sources = (await db.execute(select(func.count(KnowledgeSource.id)))).scalar() or 0
        total_chunks = (await db.execute(select(func.count(KnowledgeChunk.id)))).scalar() or 0

        # Sources by type
        sources_by_type = {}
        result = await db.execute(
            select(KnowledgeSource.source_type, func.count(KnowledgeSource.id))
            .group_by(KnowledgeSource.source_type)
        )
        for row in result:
            sources_by_type[row[0]] = row[1]

        # Queries today and this week
        today = func.date(func.now())
        week_start = func.date(func.now() - text("interval '7 days'"))
        queries_today = (await db.execute(
            select(func.count(RAGQuery.id)).where(func.date(RAGQuery.created_at) == today)
        )).scalar() or 0
        queries_this_week = (await db.execute(
            select(func.count(RAGQuery.id)).where(func.date(RAGQuery.created_at) >= week_start)
        )).scalar() or 0

        # Average confidence and latency (from recent queries)
        avg_confidence = (await db.execute(
            select(func.avg(RAGQuery.confidence)).where(RAGQuery.confidence.is_not(None))
        )).scalar() or 0.0
        avg_latency_ms = (await db.execute(
            select(func.avg(RAGQuery.total_time_ms)).where(RAGQuery.total_time_ms.is_not(None))
        )).scalar() or 0

        # Top queries (by creation time)
        top_queries = []
        result = await db.execute(
            select(RAGQuery.query_text, RAGQuery.created_at, RAGQuery.confidence)
            .order_by(RAGQuery.created_at.desc())
            .limit(10)
        )
        for row in result:
            top_queries.append({
                "query": row[0][:100] + ("..." if len(row[0]) > 100 else ""),
                "created_at": row[1].isoformat() if row[1] else None,
                "confidence": float(row[2]) if row[2] else None,
            })

        # Feedback summary
        feedback_summary = {
            "total": (await db.execute(select(func.count(RAGFeedback.id)))).scalar() or 0,
            "avg_score": (await db.execute(select(func.avg(RAGFeedback.relevance_score)))).scalar() or 0.0,
            "helpful_percentage": 0.0,
        }
        helpful_count = (await db.execute(
            select(func.count(RAGFeedback.id)).where(RAGFeedback.is_helpful == True)
        )).scalar() or 0
        if feedback_summary["total"] > 0:
            feedback_summary["helpful_percentage"] = helpful_count / feedback_summary["total"] * 100

        return KnowledgeStatsResponse(
            total_sources=total_sources,
            total_chunks=total_chunks,
            sources_by_type=sources_by_type,
            queries_today=queries_today,
            queries_this_week=queries_this_week,
            avg_confidence=float(avg_confidence),
            avg_latency_ms=int(avg_latency_ms),
            top_queries=top_queries,
            feedback_summary=feedback_summary,
        )
    except Exception as e:
        logger.exception("Failed to compute stats")
        raise HTTPException(status_code=500, detail=f"Stats error: {str(e)}")
