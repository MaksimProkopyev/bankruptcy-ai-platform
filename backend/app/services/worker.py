"""AI Task Worker — processes async tasks from Redis queue.

Runs as a separate process. Picks tasks from Redis, calls AI Core,
updates results in the database.

Usage: python -m app.services.worker
"""

import asyncio
import json
import os
import time
from uuid import UUID
from datetime import datetime, timezone

import httpx
import redis.asyncio as redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.models import AITask, Document, DocumentStatus
from app.core.config import settings

AI_CORE_URL = settings.AI_CORE_URL
QUEUE_KEY = "ai_task_queue"
POLL_INTERVAL = 2  # seconds


async def process_task(task_id: str):
    """Process a single AI task."""
    async with AsyncSessionLocal() as db:
        task = await db.get(AITask, UUID(task_id))
        if not task or task.status not in ("queued", "processing"):
            return

        task.status = "processing"
        task.started_at = datetime.now(timezone.utc)
        await db.commit()

        start = time.time()

        try:
            if task.agent_name == "ocr":
                result = await _process_ocr(task, db)
            elif task.agent_name == "qualification":
                result = await _process_qualification(task)
            elif task.agent_name == "document_gen":
                result = await _process_document_gen(task)
            else:
                result = {"error": f"Unknown agent: {task.agent_name}"}

            elapsed_ms = int((time.time() - start) * 1000)

            task.status = "completed"
            task.output_data = result
            task.processing_time_ms = elapsed_ms
            task.completed_at = datetime.now(timezone.utc)

            if "confidence" in result:
                from decimal import Decimal
                task.confidence_score = Decimal(str(result["confidence"]))

        except Exception as e:
            task.status = "failed"
            task.error_message = str(e)
            task.retry_count = (task.retry_count or 0) + 1

            # Retry if under limit
            if task.retry_count < (task.max_retries or 3):
                task.status = "queued"

        await db.commit()
        print(f"[Worker] Task {task_id} ({task.agent_name}/{task.task_type}): {task.status} in {task.processing_time_ms or 0}ms")


async def _process_ocr(task: AITask, db: AsyncSession) -> dict:
    """Process OCR task — send to AI Core, update document record."""
    input_data = task.input_data or {}
    file_path = input_data.get("file_path", "")
    doc_id = input_data.get("document_id")

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{AI_CORE_URL}/ocr",
            json={
                "file_path": file_path,
                "document_type_hint": input_data.get("document_type_hint"),
            },
        )
        resp.raise_for_status()
        result = resp.json()

    # Update document record
    if doc_id:
        doc = await db.get(Document, UUID(doc_id))
        if doc:
            doc.ocr_text = result.get("extracted_text", "")
            doc.extracted_data = result.get("structured_data", {})
            doc.ai_confidence = result.get("confidence", 0)
            doc.status = DocumentStatus.extracted if result.get("confidence", 0) > 0.5 else DocumentStatus.uploaded

    return result


async def _process_qualification(task: AITask) -> dict:
    """Process qualification task via AI Core."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{AI_CORE_URL}/qualify",
            json=task.input_data,
        )
        resp.raise_for_status()
        return resp.json()


async def _process_document_gen(task: AITask) -> dict:
    """Process document generation task via AI Core."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{AI_CORE_URL}/generate-document",
            json=task.input_data,
        )
        if resp.status_code == 501:
            return {"note": "Document generation pending implementation"}
        resp.raise_for_status()
        return resp.json()


async def run_worker():
    """Main worker loop — poll Redis queue for tasks."""
    r = redis.from_url(settings.REDIS_URL)
    print(f"[Worker] Started. Polling {QUEUE_KEY} every {POLL_INTERVAL}s...")

    while True:
        try:
            # Try to pop a task from the queue
            task_data = await r.rpop(QUEUE_KEY)

            if task_data:
                task_id = task_data.decode() if isinstance(task_data, bytes) else task_data
                await process_task(task_id)
            else:
                # No tasks, also check DB for queued tasks (fallback)
                async with AsyncSessionLocal() as db:
                    result = await db.execute(
                        select(AITask)
                        .where(AITask.status == "queued")
                        .order_by(AITask.priority, AITask.created_at)
                        .limit(1)
                    )
                    task = result.scalar_one_or_none()
                    if task:
                        await process_task(str(task.id))
                    else:
                        await asyncio.sleep(POLL_INTERVAL)

        except redis.ConnectionError:
            print("[Worker] Redis connection lost, retrying...")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"[Worker] Error: {e}")
            await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    asyncio.run(run_worker())
