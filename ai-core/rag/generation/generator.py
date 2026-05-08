"""
RAG answer generator with two prompt styles (lawyer/client).
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
import anthropic

from rag.config import config


logger = logging.getLogger(__name__)


class RAGGenerator:
    """Generates answers using Claude with retrieved context."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or config.anthropic_api_key
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for RAGGenerator")
        self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
        self.model = "claude-3-5-sonnet-20241022"

    async def generate(
        self,
        query: str,
        context: str,
        chunks: List[Dict[str, Any]],
        source: str = "lawyer",  # "lawyer" or "client"
    ) -> Dict[str, Any]:
        """Generate an answer."""
        if source == "lawyer":
            prompt = self._lawyer_prompt(query, context)
        else:
            prompt = self._client_prompt(query, context)

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.2,
                messages=[{"role": "user", "content": prompt}],
            )
            answer = response.content[0].text.strip()

            # Build citations
            citations = []
            for chunk in chunks[:5]:  # cite top‑5 chunks
                citations.append({
                    "chunk_id": chunk.get("chunk_id"),
                    "source_title": chunk.get("source_title", "Unknown"),
                    "chunk_index": chunk.get("chunk_index"),
                    "score": chunk.get("score", 0.0),
                })

            return {
                "answer": answer,
                "citations": citations,
                "confidence": self._estimate_confidence(chunks),
                "model": self.model,
                "source": source,
            }

        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return {
                "answer": "Извините, не удалось сгенерировать ответ. Пожалуйста, попробуйте позже.",
                "citations": [],
                "confidence": 0.0,
                "model": self.model,
                "source": source,
            }

    def _lawyer_prompt(self, query: str, context: str) -> str:
        return f"""Ты — опытный юрист по банкротству. Ответь на вопрос, используя только предоставленные правовые материалы.

Вопрос: {query}

Контекст (фрагменты из базы знаний):
{context}

Требования:
1. Ответ должен быть точным, ссылаться на конкретные нормы права или судебную практику.
2. Укажи, из какого источника взята информация (например, "Согласно п. 3 ст. 213.4 ФЗ «О банкротстве»...").
3. Если в контексте нет достаточной информации, честно скажи об этом.
4. Избегай предположений и домыслов.
5. Формулируй ответ профессионально, но понятно.

Ответ:"""

    def _client_prompt(self, query: str, context: str) -> str:
        return f"""Ты — помощник по банкротству, который объясняет клиентам сложные правовые вопросы простым языком.

Вопрос клиента: {query}

Контекст (фрагменты из базы знаний):
{context}

Требования:
1. Объясни ситуацию простыми словами, без юридического жаргона.
2. Если есть конкретные нормы — упомяни их, но в скобках дай пояснение.
3. Будь доброжелательным и ободряющим.
4. Если информации недостаточно, предложи обратиться к юристу за консультацией.
5. Ответ должен быть полезным и практичным.

Ответ:"""

    def _estimate_confidence(self, chunks: List[Dict[str, Any]]) -> float:
        """Heuristic confidence based on retrieval scores."""
        if not chunks:
            return 0.0
        avg_score = sum(c.get("score", 0.0) for c in chunks) / len(chunks)
        # Normalize to 0‑1
        return min(avg_score * 2.0, 1.0)