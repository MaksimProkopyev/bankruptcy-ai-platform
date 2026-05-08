"""
Full‑text search (PostgreSQL FTS) for Russian legal texts.
"""

import logging
from typing import List, Optional, Dict, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from rag.config import config


logger = logging.getLogger(__name__)


class FTSSearch:
    """Full‑text search using PostgreSQL tsvector."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
        min_rank: float = 0.05,
    ) -> List[Dict[str, Any]]:
        """Search via FTS."""
        top_k = top_k or config.top_k
        filter_clause = ""
        params = {"query": query, "top_k": top_k, "min_rank": min_rank}

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

        # Use Russian stemmer (russian_ispell) and simple ranking
        query_sql = text(f"""
            SELECT
                id, source_id, source_type, source_title,
                chunk_text, chunk_index, token_count, metadata,
                ts_rank_cd(fts_index, plainto_tsquery('russian', :query)) AS rank
            FROM knowledge_chunks
            WHERE fts_index @@ plainto_tsquery('russian', :query)
            {filter_clause}
            ORDER BY rank DESC
            LIMIT :top_k
        """)

        result = await self.db.execute(query_sql, params)
        rows = result.mappings().all()

        results = []
        for row in rows:
            if row["rank"] < min_rank:
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
                "score": float(row["rank"]),
            })

        logger.debug(f"FTS search returned {len(results)} results")
        return results