"""AI Worker — processes queued AI tasks (OCR, qualification, generation).

Listens to Redis for new tasks, runs appropriate agent, updates database.
"""

import asyncio
import json
import logging
import time
from uuid import UUID

import redis.asyncio as redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import get_db as backend_get_db
from app.models.models import AITask, Document, DocumentStatus
from ocr.engine import get_ocr_engine
from agents.ocr_extraction import OCRAgent
from agents.qualification import QualificationAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection (reuse backend's async engine)
DATABASE_URL = "postgresql+asyncpg://postgres:postgres@postgres:5432/bankruptcy"
engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Redis
REDIS_URL = "redis://redis:6379"


async def get_redis():
    return redis.from_url(REDIS_URL, decode_responses=True)


class AIWorker:
    def __init__(self):
        self.redis = None
        self.ocr_engine = get_ocr_engine()
        self.ocr_agent = OCRAgent()
        self.qualification_agent = QualificationAgent()

    async def connect(self):
        """Connect to Redis and DB."""
        self.redis = await get_redis()
        logger.info("AI Worker connected to Redis")

    async def process_task(self, task_id: UUID):
        """Process a single AI task."""
        async with AsyncSessionLocal() as db:
            task = await db.get(AITask, task_id)
            if not task:
                logger.error(f"Task {task_id} not found")
                return

            if task.status == "completed":
                logger.info(f"Task {task_id} already completed")
                return

            task.status = "processing"
            task.started_at = time.time()
            await db.commit()

            try:
                if task.agent_name == "ocr" and task.task_type == "document_extraction":
                    await self._process_ocr_task(db, task)
                elif task.agent_name == "qualification":
                    await self._process_qualification_task(db, task)
                elif task.agent_name == "document_generation":
                    await self._process_document_generation(db, task)
                else:
                    logger.warning(f"Unknown agent {task.agent_name}/{task.task_type}")
                    task.status = "failed"
                    task.error_message = f"Unknown agent {task.agent_name}"
                    await db.commit()
                    return

                task.status = "completed"
                task.completed_at = time.time()
                task.processing_time_ms = int((task.completed_at - task.started_at) * 1000)
                await db.commit()
                logger.info(f"Task {task_id} completed successfully")

            except Exception as e:
                logger.exception(f"Task {task_id} failed: {e}")
                task.status = "failed"
                task.error_message = str(e)
                task.retry_count += 1
                if task.retry_count >= task.max_retries:
                    task.status = "failed_permanently"
                await db.commit()

    async def _process_ocr_task(self, db: AsyncSession, task: AITask):
        """OCR + data extraction pipeline."""
        input_data = task.input_data
        document_id = input_data.get("document_id")
        file_path = input_data.get("file_path")
        type_hint = input_data.get("document_type_hint")

        if not document_id or not file_path:
            raise ValueError("Missing document_id or file_path in task input")

        # 1. Load document
        doc = await db.get(Document, UUID(document_id))
        if not doc:
            raise ValueError(f"Document {document_id} not found")

        # 2. Run OCR
        logger.info(f"Running OCR on {file_path}")
        ocr_text = self.ocr_engine.extract_text(file_path)
        doc.ocr_text = ocr_text
        doc.status = DocumentStatus.extracted
        await db.flush()

        # 3. Extract structured data
        logger.info(f"Running extraction for {type_hint}")
        result = await self.ocr_agent.process_document(ocr_text, type_hint)
        doc.extracted_data = result["extracted_data"]
        doc.ai_confidence = result["confidence"]
        doc.status = DocumentStatus.validated if result["confidence"] > 0.7 else DocumentStatus.extracted

        # 4. Update task output
        task.output_data = {
            "document_type": result["document_type"],
            "confidence": result["confidence"],
            "warnings": result["warnings"],
            "extracted_fields": list(result["extracted_data"].keys()),
        }
        task.confidence_score = result["confidence"]

        logger.info(f"OCR completed for document {document_id}, type {result['document_type']}")

    async def _process_qualification_task(self, db: AsyncSession, task: AITask):
        """Qualification scoring."""
        # TODO: implement
        pass

    async def _process_document_generation(self, db: AsyncSession, task: AITask):
        """Generate legal document."""
        # TODO: implement
        pass

    async def run(self):
        """Main loop: poll Redis for new tasks."""
        await self.connect()
        logger.info("AI Worker started")

        while True:
            try:
                # Get task ID from Redis queue
                task_id_str = await self.redis.lpop("ai_tasks")
                if task_id_str:
                    task_id = UUID(task_id_str)
                    logger.info(f"Processing task {task_id}")
                    await self.process_task(task_id)
                else:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Error in worker loop: {e}")
                await asyncio.sleep(5)


if __name__ == "__main__":
    worker = AIWorker()
    asyncio.run(worker.run())