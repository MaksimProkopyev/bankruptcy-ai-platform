"""
Ingestion pipeline orchestrator: parse → chunk → embed → index.
"""

import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from rag.config import config
from rag.ingestion.parser import get_parser, ParsedDocument
from rag.ingestion.chunker import LegalChunker, Chunk
from rag.ingestion.embedder import EmbeddingService
from rag.ingestion.indexer import KnowledgeIndexer


logger = logging.getLogger(__name__)


class IngestionPipeline:
    """Orchestrates the ingestion process."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.chunker = LegalChunker()
        self.embedder = EmbeddingService()
        self.indexer = KnowledgeIndexer(db, self.embedder)

    async def ingest(
        self,
        source_type: str,
        title: str,
        content: str,
        source_id: str,
        metadata: Optional[dict] = None,
    ) -> int:
        """Ingest a document into the knowledge base."""
        logger.info(f"Ingesting source {source_id} ({source_type}): {title}")

        # 1. Parse
        parser = get_parser(source_type)
        parsed: ParsedDocument = parser.parse(content, title=title, **metadata or {})
        logger.debug(f"Parsed into {len(parsed.sections)} sections")

        # 2. Chunk
        all_chunks = []
        for section in parsed.sections:
            chunks = self.chunker.chunk(section["content"], metadata=section["metadata"])
            all_chunks.extend(chunks)
        logger.debug(f"Created {len(all_chunks)} chunks")

        # 3. Index
        inserted = await self.indexer.index_chunks(
            chunks=all_chunks,
            source_id=source_id,
            source_type=source_type,
            source_title=title,
            metadata=metadata,
        )

        logger.info(f"Ingestion completed, indexed {inserted} chunks")
        return inserted