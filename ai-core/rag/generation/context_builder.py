"""
Builds a coherent context from retrieved chunks.
"""

import logging
from typing import List, Dict, Any

from rag.config import config


logger = logging.getLogger(__name__)


class ContextBuilder:
    """Assembles retrieved chunks into a single context string."""

    def __init__(self, max_context_tokens: int | None = None):
        self.max_context_tokens = max_context_tokens or config.max_context_tokens

    def build(
        self,
        chunks: List[Dict[str, Any]],
        include_metadata: bool = False,
    ) -> str:
        """Build a readable context."""
        if not chunks:
            return ""

        parts = []
        total_tokens = 0

        for chunk in chunks:
            text = chunk.get("chunk_text", "")
            if not text:
                continue

            # Estimate token count (rough)
            token_est = len(text.split())  # simplistic
            if total_tokens + token_est > self.max_context_tokens:
                logger.warning(f"Context token limit reached ({self.max_context_tokens})")
                break

            if include_metadata:
                source = chunk.get("source_title", "Unknown")
                idx = chunk.get("chunk_index", 0)
                header = f"[Источник: {source}, фрагмент {idx}]"
                parts.append(f"{header}\n{text}")
            else:
                parts.append(text)

            total_tokens += token_est

        context = "\n\n---\n\n".join(parts)
        logger.debug(f"Built context of {total_tokens} estimated tokens, {len(parts)} chunks")
        return context