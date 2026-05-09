"""
Pydantic models for RAG v2 API requests and responses.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


# ---- Search ----

class KnowledgeSearchRequest(BaseModel):
    """Request for hybrid search."""
    query: str = Field(..., description="Search query")
    filters: Optional[Dict[str, Any]] = Field(None, description="Filters by source type, tags, etc.")
    top_k: Optional[int] = Field(5, ge=1, le=100, description="Number of results to return")
    include_highlight: Optional[bool] = Field(False, description="Include highlighted snippets")


class SearchResult(BaseModel):
    """Single search result."""
    chunk_id: UUID
    source_id: UUID
    source_type: str
    source_title: str
    chunk_text: str
    chunk_index: int
    score: float
    meta: Dict[str, Any] = {}
    highlight: Optional[str] = None


class KnowledgeSearchResponse(BaseModel):
    """Response for hybrid search."""
    results: List[SearchResult]
    total: int
    query_time_ms: int


# ---- Ask ----

class KnowledgeAskRequest(BaseModel):
    """Request for Q&A with RAG."""
    query: str = Field(..., description="Question")
    case_id: Optional[UUID] = Field(None, description="Optional case ID for context")
    filters: Optional[Dict[str, Any]] = Field(None, description="Filters for retrieval")
    source: Optional[str] = Field(None, description="Target source type (law, court_practice, etc.)")


class Citation(BaseModel):
    """Citation of a source chunk."""
    chunk_id: UUID
    source_id: UUID
    source_title: str
    source_type: str
    chunk_text: str
    score: float


class KnowledgeAskResponse(BaseModel):
    """Response for Q&A."""
    answer: str
    citations: List[Citation]
    confidence: float = Field(..., ge=0.0, le=1.0)
    sources_used: List[str] = Field(..., description="Source types used")
    query_id: Optional[UUID] = Field(None, description="ID of the saved query")
    timing: Dict[str, int] = Field(..., description="Timing in ms for each step")


# ---- Sources ----

class SourceCreateRequest(BaseModel):
    """Request to create a knowledge source."""
    source_type: str = Field(..., description="law, court_practice, plenum, template, faq")
    title: str = Field(..., max_length=500)
    content: Optional[str] = Field(None, description="Raw text content (if provided, auto-ingest can be triggered)")
    tags: Optional[List[str]] = Field([])
    auto_ingest: Optional[bool] = Field(True, description="Automatically ingest content after creation")


class SourceResponse(BaseModel):
    """Response after source creation."""
    source_id: UUID
    status: str = Field(..., description="created, ingested, error")
    chunks_count: Optional[int] = Field(None, description="Number of chunks after ingestion")
    message: Optional[str] = None


# ---- Feedback ----

class FeedbackRequest(BaseModel):
    """Feedback on a search/answer result."""
    query_id: UUID = Field(..., description="ID of the query (from ask/search response)")
    chunk_id: UUID = Field(..., description="ID of the chunk being rated")
    relevance_score: int = Field(..., ge=1, le=5, description="1-5 rating")
    is_helpful: bool = Field(..., description="Whether the result was helpful")
    comment: Optional[str] = Field(None, max_length=1000)


# ---- Stats ----

class KnowledgeStatsResponse(BaseModel):
    """Statistics about the RAG system."""
    total_sources: int
    total_chunks: int
    sources_by_type: Dict[str, int]
    queries_today: int
    queries_this_week: int
    avg_confidence: float
    avg_latency_ms: int
    top_queries: List[Dict[str, Any]] = Field(..., description="Top 10 queries")
    feedback_summary: Dict[str, int] = Field(..., description="Counts of feedback ratings")


# ---- Internal models (not exposed via API) ----

class ProcessedQuery(BaseModel):
    """Result of query processing (NER, classification, etc.)."""
    original_query: str
    normalized_query: str
    entities: List[Dict[str, Any]]
    classification: str
    synonyms: List[str]
    case_context: Optional[Dict[str, Any]] = None


class RetrievedChunk(BaseModel):
    """Chunk after retrieval, before reranking."""
    chunk_id: UUID
    source_id: UUID
    text: str
    vector_score: float
    fts_score: float
    hybrid_score: float
    meta: Dict[str, Any]


# ---- SQLAlchemy ORM Models ----

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ARRAY
from sqlalchemy import ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, relationship
from pgvector.sqlalchemy import Vector
import uuid

class Base(DeclarativeBase):
    pass

class KnowledgeSource(Base):
    __tablename__ = "knowledge_sources"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_type = Column(String(50), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    content = Column(Text)
    external_url = Column(Text)
    file_path = Column(Text)
    tags = Column(ARRAY(String), default=[])
    meta = Column('metadata', JSONB, default={})
    auto_ingest = Column(Boolean, default=True)
    ingestion_status = Column(String(20), default="pending")
    chunks_count = Column(Integer, default=0)
    ingestion_started_at = Column(DateTime(timezone=True))
    ingestion_completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    chunks = relationship("KnowledgeChunk", back_populates="source", cascade="all, delete-orphan")

class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_sources.id", ondelete="CASCADE"), nullable=False)
    source_type = Column(String(50))
    source_title = Column(String(500))
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    token_count = Column(Integer)
    embedding = Column(Vector(1536))
    fts_index = Column(Text)  # tsvector stored as text, updated via trigger
    meta = Column('metadata', JSONB, default={})
    feedback_count = Column(Integer, default=0)
    avg_relevance_score = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    source = relationship("KnowledgeSource", back_populates="chunks")

class RAGQuery(Base):
    __tablename__ = "rag_queries"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_text = Column(Text, nullable=False)
    answer = Column(Text)
    confidence = Column(Float)
    total_time_ms = Column(Integer)
    filters = Column(JSONB, default={})
    sources_used = Column(ARRAY(String), default=[])
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class RAGFeedback(Base):
    __tablename__ = "rag_feedback"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_id = Column(UUID(as_uuid=True), ForeignKey("rag_queries.id"))
    chunk_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_chunks.id"))
    relevance_score = Column(Integer)
    is_helpful = Column(Boolean)
    comment = Column(Text)
    created_by = Column(UUID(as_uuid=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())