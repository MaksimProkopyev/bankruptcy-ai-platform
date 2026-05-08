"""
Knowledge indexer: stores chunks in pgvector with FTS.
"""

import logging
from uuid import uuid4
from typing import List, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from rag.config import config
from rag.ingestion.chunker import Chunk
from rag.ingestion.embedder import EmbeddingService


logger = logging.getLogger(__name__)


class KnowledgeIndexer:
    """Indexes text chunks into PostgreSQL (pgvector + FTS)."""

    def __init__(self, db: AsyncSession, embedder: Optional[EmbeddingService] = None):
        self.db = db
        self.embedder = embedder or EmbeddingService()

    async def index_chunks(
        self,
        chunks: List[Chunk],
        source_id: str,
        source_type: str,
        source_title: str,
        metadata: Optional[dict] = None,
    ) -> int:
        """Index a list of chunks."""
        if not chunks:
            return 0

        texts = [chunk.text for chunk in chunks]
        embeddings = await self.embedder.embed(texts)

        inserted = 0
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = str(uuid4())
            await self.db.execute(
                text("""
                    INSERT INTO knowledge_chunks
                    (id, source_id, source_type, source_title,
                     chunk_text, chunk_index, token_count,
                     embedding, fts_vector, metadata)
                    VALUES
                    (:id, :source_id, :source_type, :source_title,
                     :chunk_text, :chunk_index, :token_count,
                     :embedding, to_tsvector('russian', :chunk_text), :metadata)
                """),
                {
                    "id": chunk_id,
                    "source_id": source_id,
                    "source_type": source_type,
                    "source_title": source_title,
                    "chunk_text": chunk.text,
                    "chunk_index": i,
                    "token_count": chunk.token_count,
                    "embedding": str(embedding),
                    "metadata": metadata or {},
                }
            )
            inserted += 1

        await self.db.commit()
        logger.info(f"Indexed {inserted} chunks for source {source_id}")
        return inserted

    async def delete_source(self, source_id: str) -> int:
        """Delete all chunks belonging to a source."""
        result = await self.db.execute(
            text("DELETE FROM knowledge_chunks WHERE source_id = :source_id"),
            {"source_id": source_id}
        )
        await self.db.commit()
        deleted = result.rowcount
        logger.info(f"Deleted {deleted} chunks for source {source_id}")
        return deleted