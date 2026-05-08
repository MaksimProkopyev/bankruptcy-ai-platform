"""
RAG v2 configuration using pydantic-settings.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class RAGConfig(BaseSettings):
    """Configuration for RAG v2."""

    model_config = SettingsConfigDict(
        env_prefix="RAG_",
        case_sensitive=False,
        env_file=".env",
        extra="ignore",
    )

    # OpenAI API for embeddings
    openai_api_key: str = os.environ.get("OPENAI_API_KEY", "")
    embedding_model: str = "text-embedding-3-small"
    embedding_batch_size: int = 32
    embedding_dimensions: int = 1536

    # Anthropic API for reranking and generation
    anthropic_api_key: str = os.environ.get("ANTHROPIC_API_KEY", "")
    reranker_model: str = "claude-sonnet-4-20250514"
    generator_model: str = "claude-sonnet-4-20250514"

    # PostgreSQL connection
    database_url: str = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@postgres:5432/bankruptcy"
    )

    # Chunking
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # Retrieval
    top_k: int = 10
    hybrid_alpha: float = 0.5  # weight for vector vs FTS
    rrf_k: int = 60  # reciprocal rank fusion parameter
    rerank_top_n: int = 5

    # Generation
    max_context_tokens: int = 4000
    max_answer_tokens: int = 1500

    # Source types
    source_types: list[str] = ["law", "court_practice", "plenum", "template", "faq"]

    # Logging
    log_level: str = "INFO"
    enable_metrics: bool = True

    @property
    def has_openai(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def has_anthropic(self) -> bool:
        return bool(self.anthropic_api_key)


# Global config instance
config = RAGConfig()