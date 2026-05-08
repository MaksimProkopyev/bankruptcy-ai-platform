"""RAG pipeline — index legal documents and search with embeddings.

Indexes: ФЗ-127, АПК, ГК, court decisions, internal templates.
Uses pgvector for similarity search.
"""

import os
import json
from uuid import uuid4
from dataclasses import dataclass

import anthropic
import httpx
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class SearchResult:
    chunk_text: str
    source_name: str
    source_type: str
    score: float
    metadata: dict


class RAGPipeline:
    """RAG over legal knowledge base using pgvector."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.anthropic = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY", "")
        )

    async def index_document(
        self,
        text_content: str,
        source_name: str,
        source_type: str,  # law, court_decision, template, faq
        source_url: str | None = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        metadata: dict | None = None,
    ) -> int:
        """Split document into chunks, embed, and store in pgvector."""
        chunks = self._split_text(text_content, chunk_size, chunk_overlap)
        count = 0

        for i, chunk in enumerate(chunks):
            embedding = await self._get_embedding(chunk)

            await self.db.execute(
                text("""
                    INSERT INTO knowledge_base 
                    (id, source_type, source_name, source_url, chunk_text, chunk_index, embedding, metadata)
                    VALUES (:id, :source_type, :source_name, :source_url, :chunk_text, :chunk_index, :embedding, :metadata)
                """),
                {
                    "id": str(uuid4()),
                    "source_type": source_type,
                    "source_name": source_name,
                    "source_url": source_url,
                    "chunk_text": chunk,
                    "chunk_index": i,
                    "embedding": str(embedding),
                    "metadata": json.dumps(metadata or {}),
                },
            )
            count += 1

        await self.db.commit()
        return count

    async def search(
        self,
        query: str,
        top_k: int = 5,
        source_type: str | None = None,
        min_score: float = 0.5,
    ) -> list[SearchResult]:
        """Semantic search over knowledge base."""
        query_embedding = await self._get_embedding(query)

        filter_clause = ""
        if source_type:
            filter_clause = f"AND source_type = '{source_type}'"

        result = await self.db.execute(
            text(f"""
                SELECT 
                    chunk_text, source_name, source_type, metadata,
                    1 - (embedding <=> :embedding::vector) AS score
                FROM knowledge_base
                WHERE 1=1 {filter_clause}
                ORDER BY embedding <=> :embedding::vector
                LIMIT :top_k
            """),
            {"embedding": str(query_embedding), "top_k": top_k},
        )

        results = []
        for row in result.mappings().all():
            score = float(row["score"])
            if score >= min_score:
                results.append(SearchResult(
                    chunk_text=row["chunk_text"],
                    source_name=row["source_name"],
                    source_type=row["source_type"],
                    score=score,
                    metadata=json.loads(row["metadata"]) if isinstance(row["metadata"], str) else row["metadata"] or {},
                ))

        return results

    async def answer_with_context(
        self,
        question: str,
        top_k: int = 5,
        source_type: str | None = None,
    ) -> dict:
        """Search knowledge base and generate answer with citations."""
        results = await self.search(question, top_k=top_k, source_type=source_type)

        if not results:
            return {
                "answer": "По данному вопросу информация в базе знаний не найдена.",
                "sources": [],
                "confidence": 0,
            }

        context = "\n\n---\n\n".join([
            f"[Источник: {r.source_name}]\n{r.chunk_text}"
            for r in results
        ])

        response = self.anthropic.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system="""Ты — AI-юрист, специализирующийся на банкротстве физических лиц в РФ.

Отвечай на вопросы ТОЛЬКО на основе предоставленного контекста.
Если в контексте нет ответа — скажи об этом прямо.
Всегда указывай источник (название закона, статью, пункт).
Отвечай кратко и по существу.
НЕ давай юридических гарантий.""",
            messages=[{
                "role": "user",
                "content": f"Контекст из базы знаний:\n\n{context}\n\n---\n\nВопрос: {question}",
            }],
        )

        return {
            "answer": response.content[0].text,
            "sources": [
                {"name": r.source_name, "type": r.source_type, "score": round(r.score, 3)}
                for r in results
            ],
            "confidence": round(results[0].score, 3) if results else 0,
        }

    async def _get_embedding(self, text: str) -> list[float]:
        """Get embedding vector via OpenAI API (Claude doesn't have embeddings yet)."""
        openai_key = os.environ.get("OPENAI_API_KEY", "")
        if not openai_key:
            # Fallback: return zero vector for testing
            return [0.0] * 1536

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {openai_key}"},
                json={"model": "text-embedding-3-small", "input": text},
                timeout=30.0,
            )
            data = response.json()
            return data["data"][0]["embedding"]

    def _split_text(
        self, text: str, chunk_size: int, overlap: int
    ) -> list[str]:
        """Split text into overlapping chunks by sentences."""
        sentences = text.replace("\n\n", "\n").split(".")
        chunks = []
        current_chunk = ""

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            if len(current_chunk) + len(sentence) > chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                # Keep overlap
                words = current_chunk.split()
                overlap_words = words[-overlap // 5:] if len(words) > overlap // 5 else words
                current_chunk = " ".join(overlap_words) + ". " + sentence + "."
            else:
                current_chunk += " " + sentence + "."

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks


# ---- Seed data: key articles from ФЗ-127 ----

FZ127_KEY_ARTICLES = [
    {
        "source_name": "ФЗ-127 ст. 213.3 — Условия подачи заявления",
        "text": """Заявление о признании гражданина банкротом принимается арбитражным судом при условии, что требования к гражданину составляют не менее чем пятьсот тысяч рублей и указанные требования не исполнены в течение трёх месяцев с даты, когда они должны быть исполнены. Гражданин обязан обратиться в арбитражный суд с заявлением о признании его банкротом в случае, если размер обязательств и обязанности по уплате обязательных платежей составляет не менее чем пятьсот тысяч рублей.""",
    },
    {
        "source_name": "ФЗ-127 ст. 213.4 — Заявление гражданина о банкротстве",
        "text": """Гражданин обязан обратиться в арбитражный суд с заявлением о признании его банкротом не позднее тридцати рабочих дней со дня, когда он узнал или должен был узнать о том, что удовлетворение требований одного кредитора или нескольких кредиторов приводит к невозможности исполнения обязательств перед другими кредиторами. К заявлению прилагаются документы, подтверждающие наличие задолженности, основание её возникновения и неспособность гражданина удовлетворить требования кредиторов в полном объёме.""",
    },
    {
        "source_name": "ФЗ-127 ст. 213.11 — Последствия введения реструктуризации",
        "text": """С даты вынесения арбитражным судом определения о признании обоснованным заявления о признании гражданина банкротом и введении реструктуризации его долгов вводится мораторий на удовлетворение требований кредиторов, прекращается начисление неустоек и иных финансовых санкций, приостанавливается исполнительное производство по имущественным взысканиям.""",
    },
    {
        "source_name": "ФЗ-127 ст. 213.25 — Имущество, исключаемое из конкурсной массы",
        "text": """Из конкурсной массы исключается имущество, на которое не может быть обращено взыскание в соответствии с гражданским процессуальным законодательством, в том числе единственное пригодное для постоянного проживания жилое помещение, если оно не является предметом ипотеки. Также исключаются предметы обычной домашней обстановки и обихода, вещи индивидуального пользования, продукты питания и денежные средства на общую сумму не менее установленной величины прожиточного минимума.""",
    },
    {
        "source_name": "ФЗ-127 ст. 213.28 — Освобождение от обязательств",
        "text": """После завершения расчётов с кредиторами гражданин, признанный банкротом, освобождается от дальнейшего исполнения требований кредиторов. Освобождение гражданина от обязательств не допускается, если при возникновении или исполнении обязательств гражданин действовал незаконно, предоставлял кредиторам заведомо ложные сведения, скрыл или умышленно уничтожил имущество. Требования о возмещении вреда, причинённого жизни или здоровью, о выплате заработной платы и алиментов не подлежат списанию.""",
    },
    {
        "source_name": "ФЗ-127 ст. 223.2 — Внесудебное банкротство",
        "text": """Гражданин, общий размер денежных обязательств которого составляет не менее двадцати пяти тысяч рублей и не более одного миллиона рублей, имеет право обратиться с заявлением о признании его банкротом во внесудебном порядке при условии, что на дату подачи заявления в отношении него окончено исполнительное производство в связи с возвращением исполнительного документа взыскателю. Внесудебное банкротство осуществляется через многофункциональный центр предоставления государственных и муниципальных услуг (МФЦ).""",
    },
]
