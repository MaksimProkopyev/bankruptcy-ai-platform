"""
Reranker using Claude API to improve relevance.
"""

import logging
import asyncio
from typing import List, Dict, Any
import anthropic

from rag.config import config


logger = logging.getLogger(__name__)


class ClaudeReranker:
    """LLM‑based reranker for legal retrieval."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or config.anthropic_api_key
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for ClaudeReranker")
        self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
        self.model = "claude-3-5-sonnet-20241022"

    async def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_n: int = 5,
    ) -> List[Dict[str, Any]]:
        """Rerank candidates using Claude."""
        if not candidates:
            return []

        # Prepare context
        context_parts = []
        for i, cand in enumerate(candidates[:20]):  # limit to avoid huge prompt
            text = cand.get("chunk_text", "")[:1000]
            context_parts.append(f"[{i+1}] {text}")

        context = "\n\n".join(context_parts)

        prompt = f"""Ты — эксперт по российскому праву. Пользователь задал вопрос:

"{query}"

Ниже приведены фрагменты текста из базы знаний (пронумерованы). Оцени, насколько каждый фрагмент релевантен вопросу, и верни номера самых релевантных (не более {top_n}), в порядке убывания релевантности.

Фрагменты:

{context}

Верни только номера самых релевантных фрагментов через запятую, например: "3, 1, 5". Не добавляй пояснений."""

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=100,
                temperature=0.0,
                messages=[{"role": "user", "content": prompt}],
            )
            content = response.content[0].text.strip()
            logger.debug(f"Claude rerank response: {content}")

            # Parse numbers
            selected_indices = []
            for part in content.split(","):
                part = part.strip()
                if part.isdigit():
                    idx = int(part) - 1  # convert to zero‑based
                    if 0 <= idx < len(candidates):
                        selected_indices.append(idx)

            # Keep original order but only selected
            selected = [candidates[i] for i in selected_indices if i < len(candidates)]
            # If Claude returned nothing, fall back to original order
            if not selected:
                selected = candidates[:top_n]

            logger.info(f"Reranked {len(candidates)} → {len(selected)} chunks")
            return selected[:top_n]

        except Exception as e:
            logger.error(f"Claude rerank failed: {e}")
            # Fallback: return top‑N by original score
            sorted_by_score = sorted(candidates, key=lambda x: x.get("score", 0), reverse=True)
            return sorted_by_score[:top_n]