"""
Vector search using pgvector cosine similarity.
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from rag.config import config


logger = logging.getLogger(__name__)


class VectorSearch:
    """Semantic search via pgvector."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def search(
        self,
        embedding: List[float],
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
        min_score: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """Search for similar chunks."""
        top_k = top_k or config.top_k
        filter_clause = ""
        params = {"embedding": str(embedding), "top_k": top_k, "min_score": min_score}

        if filters:
            conditions = []
            if "source_type" in filters:
                conditions.append("source_type = :source_type")
                params["source_type"] = filters["source_type"]
            if "source_id" in filters:
                conditions.append("source_id = :source_id")
                params["source_id"] = filters["source_id"]
            if conditions:
                filter_clause = "AND " + " AND ".join(conditions)

        query = text(f"""
            SELECT
                id, source_id, source_type, source_title,
                chunk_text, chunk_index, token_count, metadata,
                1 - (embedding <=> :embedding::vector) AS score
            FROM knowledge_chunks
            WHERE 1=1 {filter_clause}
            ORDER BY embedding <=> :embedding::vector
            LIMIT :top_k
        """)

        result = await self.db.execute(query, params)
        rows = result.mappings().all()

        results = []
        for row in rows:
            if row["score"] < min_score:
                continue
            results.append({
                "chunk_id": row["id"],
                "source_id": row["source_id"],
                "source_type": row["source_type"],
                "source_title": row["source_title"],
                "chunk_text": row["chunk_text"],
                "chunk_index": row["chunk_index"],
                "token_count": row["token_count"],
                "metadata": row["metadata"] or {},
                "score": float(row["score"]),
            })

        logger.debug(f"Vector search returned {len(results)} results")
        return results