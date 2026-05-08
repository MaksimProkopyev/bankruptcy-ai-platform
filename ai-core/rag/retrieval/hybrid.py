"""
Hybrid retrieval (vector + FTS) with Reciprocal Rank Fusion (RRF).
"""

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from rag.retrieval.vector_search import VectorSearch
from rag.retrieval.fts_search import FTSSearch
from rag.config import config


logger = logging.getLogger(__name__)


class HybridRetriever:
    """Combines vector and full‑text search using RRF."""

    def __init__(
        self,
        db: AsyncSession,
        vector_weight: float = 0.6,
        fts_weight: float = 0.4,
        rrf_k: int = 60,
    ):
        self.vector_search = VectorSearch(db)
        self.fts_search = FTSSearch(db)
        self.vector_weight = vector_weight
        self.fts_weight = fts_weight
        self.rrf_k = rrf_k

    async def search(
        self,
        query: str,
        embedding: List[float],
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Run hybrid search and fuse results."""
        top_k = top_k or config.top_k

        # Parallel retrieval
        vector_results = await self.vector_search.search(
            embedding=embedding,
            top_k=top_k * 2,  # fetch more for fusion
            filters=filters,
        )
        fts_results = await self.fts_search.search(
            query=query,
            top_k=top_k * 2,
            filters=filters,
        )

        # Apply weights
        for r in vector_results:
            r["score"] *= self.vector_weight
        for r in fts_results:
            r["score"] *= self.fts_weight

        # RRF fusion
        fused = self._rrf_fusion(vector_results, fts_results, top_k)
        logger.info(f"Hybrid search fused {len(vector_results)} vector + {len(fts_results)} FTS → {len(fused)} results")
        return fused

    def _rrf_fusion(
        self,
        vec_results: List[Dict[str, Any]],
        fts_results: List[Dict[str, Any]],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """Reciprocal Rank Fusion."""
        # Build mapping chunk_id -> (vector_rank, fts_rank)
        vec_ranks = {}
        for i, r in enumerate(vec_results):
            vec_ranks[r["chunk_id"]] = i + 1

        fts_ranks = {}
        for i, r in enumerate(fts_results):
            fts_ranks[r["chunk_id"]] = i + 1

        all_ids = set(vec_ranks.keys()) | set(fts_ranks.keys())
        scores = {}
        for chunk_id in all_ids:
            vec_rank = vec_ranks.get(chunk_id, self.rrf_k + 1)
            fts_rank = fts_ranks.get(chunk_id, self.rrf_k + 1)
            rrf_score = 1 / (self.rrf_k + vec_rank) + 1 / (self.rrf_k + fts_rank)
            scores[chunk_id] = rrf_score

        # Sort by RRF score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:top_k]

        # Reconstruct results with original data
        chunk_map = {}
        for r in vec_results + fts_results:
            if r["chunk_id"] not in chunk_map:
                chunk_map[r["chunk_id"]] = r

        fused = []
        for chunk_id in sorted_ids:
            chunk = chunk_map.get(chunk_id)
            if chunk:
                chunk = chunk.copy()
                chunk["score"] = scores[chunk_id]
                fused.append(chunk)

        return fused