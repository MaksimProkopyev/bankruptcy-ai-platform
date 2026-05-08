"""
Embedding service using OpenAI batch API.
"""

import asyncio
import logging
from typing import List, Optional
import httpx

from rag.config import config


logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating embeddings via OpenAI API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        batch_size: Optional[int] = None,
    ):
        self.api_key = api_key or config.openai_api_key
        self.model = model or config.embedding_model
        self.batch_size = batch_size or config.embedding_batch_size
        self.dimensions = config.embedding_dimensions
        self.base_url = "https://api.openai.com/v1"
        self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Lazy HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of texts."""
        if not self.api_key:
            logger.warning("OpenAI API key not set, returning zero vectors")
            return [[0.0] * self.dimensions for _ in texts]

        embeddings = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            try:
                batch_embeddings = await self._embed_batch(batch)
                embeddings.extend(batch_embeddings)
            except Exception as e:
                logger.error(f"Embedding batch failed: {e}")
                # Fallback to zero vectors for failed batch
                embeddings.extend([[0.0] * self.dimensions for _ in batch])
        return embeddings

    async def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Call OpenAI embedding API for a batch."""
        response = await self.client.post(
            f"{self.base_url}/embeddings",
            json={
                "model": self.model,
                "input": texts,
                "dimensions": self.dimensions,
            },
        )
        if response.status_code != 200:
            raise RuntimeError(f"OpenAI API error: {response.text}")
        data = response.json()
        return [item["embedding"] for item in data["data"]]

    async def embed_query(self, query: str) -> List[float]:
        """Embed a single query (convenience method)."""
        results = await self.embed([query])
        return results[0]

    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None