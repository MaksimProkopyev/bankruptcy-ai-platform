"""AI API — proxy to AI Core service."""

import time
from uuid import UUID, uuid4
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import httpx

from app.db.session import get_db
from app.models.models import AITask, Case, CaseEvent, Client
from app.core.config import settings
from app.schemas.schemas import (
    AITaskRequest, AITaskResponse,
    QualificationInput, QualificationResult,
    LeadCreate, LeadResponse,
    ConsultantMessageRequest, ConsultantMessageResponse,
)
from app.core.permissions import require_permission

router = APIRouter()


@router.post("/qualify", response_model=QualificationResult)
async def qualify_lead(data: QualificationInput, db: AsyncSession = Depends(get_db)):
    """Run AI qualification scoring on a lead."""
    # Create AI task record
    task = AITask(
        agent_name="qualification",
        task_type="lead_scoring",
        status="processing",
        priority=1,
        input_data=data.model_dump(mode="json"),
    )
    db.add(task)
    await db.flush()

    start_time = time.time()

    # Call AI Core
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.AI_CORE_URL}/qualify",
                json=data.model_dump(mode="json"),
            )
            resp.raise_for_status()
            result = resp.json()

        processing_time_ms = int((time.time() - start_time) * 1000)

        task.status = "completed"
        task.output_data = result
        task.confidence_score = result.get("confidence")
        task.processing_time_ms = processing_time_ms
        # llm_tokens_used and llm_cost could be extracted from AI Core response if available
        # For now, leave as None
        await db.commit()
        return result

    except httpx.HTTPError as e:
        task.status = "failed"
        task.error_message = str(e)
        await db.commit()
        raise HTTPException(status_code=502, detail=f"AI Core error: {e}")


@router.post("/chat")
async def chat(
    messages: list[dict],
    session_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Proxy chat to AI Core chatbot."""
    # Create AI task record for chat
    task = AITask(
        agent_name="chatbot",
        task_type="conversation",
        status="processing",
        priority=5,
        input_data={"messages": messages, "session_id": session_id},
    )
    db.add(task)
    await db.flush()

    start_time = time.time()

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.AI_CORE_URL}/chat",
                json={"messages": messages, "session_id": session_id},
            )
            resp.raise_for_status()
            result = resp.json()

        processing_time_ms = int((time.time() - start_time) * 1000)

        task.status = "completed"
        task.output_data = result
        task.processing_time_ms = processing_time_ms
        await db.commit()
        return result

    except httpx.HTTPError as e:
        task.status = "failed"
        task.error_message = str(e)
        await db.commit()
        raise HTTPException(status_code=502, detail=f"AI Core error: {e}")


@router.post("/lead", response_model=LeadResponse, status_code=201)
async def create_lead_from_chatbot(data: LeadCreate, db: AsyncSession = Depends(get_db)):
    """Create a lead (Client + Case) after chatbot qualification."""
    # 1. Create or find existing client by phone/email
    client_data = data.client
    existing_client = None
    if client_data.phone:
        stmt = select(Client).where(Client.phone == client_data.phone)
        result = await db.execute(stmt)
        existing_client = result.scalar_one_or_none()
    if not existing_client and client_data.email:
        stmt = select(Client).where(Client.email == client_data.email)
        result = await db.execute(stmt)
        existing_client = result.scalar_one_or_none()

    if existing_client:
        client = existing_client
        # Update UTM fields if provided
        if data.utm_source:
            client.utm_source = data.utm_source
        if data.utm_medium:
            client.utm_medium = data.utm_medium
        if data.utm_campaign:
            client.utm_campaign = data.utm_campaign
        if data.lead_source:
            client.lead_source = data.lead_source
    else:
        client = Client(
            first_name=client_data.first_name,
            last_name=client_data.last_name,
            patronymic=client_data.patronymic,
            phone=client_data.phone,
            email=client_data.email,
            birth_date=client_data.birth_date,
            region=client_data.region,
            marital_status=client_data.marital_status,
            is_employed=client_data.is_employed,
            monthly_income=client_data.monthly_income,
            utm_source=data.utm_source,
            utm_medium=data.utm_medium,
            utm_campaign=data.utm_campaign,
            lead_source=data.lead_source,
        )
        db.add(client)
    await db.flush()

    # 2. Create case
    qualification = data.qualification
    case = Case(
        client_id=client.id,
        status="lead",
        procedure_type=qualification.procedure_type or "undetermined",
        total_debt=qualification.estimated_cost,  # временно, можно позже уточнить
        ai_score=qualification.confidence,
        ai_recommended_procedure=qualification.recommended_procedure,
        ai_risk_level=qualification.risk_level,
        ai_scoring_details={
            "risk_factors": qualification.risk_factors,
            "explanation": qualification.explanation,
            "needs_lawyer_review": qualification.needs_lawyer_review,
        },
    )
    db.add(case)
    await db.flush()

    # 3. Create AI task record for this qualification
    ai_task = AITask(
        case_id=case.id,
        agent_name="qualification",
        task_type="lead_scoring",
        status="completed",
        priority=1,
        input_data=client_data.model_dump(mode="json"),
        output_data=qualification.model_dump(mode="json"),
        confidence_score=qualification.confidence,
    )
    db.add(ai_task)

    # 4. Create system event
    event = CaseEvent(
        case_id=case.id,
        event_type="lead_created",
        title="Лид создан через чат-бота",
        description=f"Клиент {client.first_name} {client.last_name} прошел квалификацию через чат-бота. Результат: {qualification.recommended_procedure}",
        event_metadata={"source": "chatbot", "qualification_result": qualification.model_dump()},
        is_system_event=True,
        is_visible_to_client=False,
    )
    db.add(event)

    await db.commit()
    await db.refresh(client)
    await db.refresh(case)
    await db.refresh(ai_task)

    return LeadResponse(
        client=client,
        case=case,
        ai_task=ai_task,
    )


@router.post("/consultant", response_model=ConsultantMessageResponse)
async def chat_with_consultant(
    request: ConsultantMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    """Chat with FAQ-bot consultant (proxy to AI Core)."""
    # Create AI task record for tracking
    task = AITask(
        agent_name="consultant",
        task_type="chat",
        status="processing",
        priority=3,
        input_data=request.model_dump(mode="json"),
    )
    db.add(task)
    await db.flush()

    start_time = time.time()

    # Call AI Core consultant endpoint
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.AI_CORE_URL}/api/v1/chat/consultant",
                json=request.model_dump(mode="json"),
            )
            resp.raise_for_status()
            result = resp.json()
    except httpx.HTTPStatusError as e:
        task.status = "failed"
        task.error_message = f"AI Core error: {e.response.status_code}"
        await db.commit()
        raise HTTPException(
            status_code=502,
            detail=f"AI Core service error: {e.response.status_code}"
        )
    except Exception as e:
        task.status = "failed"
        task.error_message = str(e)
        await db.commit()
        raise HTTPException(status_code=500, detail="Internal server error")

    processing_time_ms = int((time.time() - start_time) * 1000)

    # Update task with success
    task.status = "completed"
    task.output_data = result
    task.processing_time_ms = processing_time_ms
    await db.commit()

    return ConsultantMessageResponse(**result)


@router.post("/tasks", response_model=AITaskResponse, status_code=201,
             dependencies=[Depends(require_permission("ai_tasks", "write"))])
async def create_ai_task(data: AITaskRequest, db: AsyncSession = Depends(get_db)):
    """Submit a task to the AI Core (OCR, document generation, etc.)."""
    task = AITask(
        case_id=data.case_id,
        agent_name=data.agent_name,
        task_type=data.task_type,
        status="queued",
        priority=5,
        input_data=data.input_data,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # Push to Redis queue (processed by worker)
    # TODO: redis.lpush(f"ai_queue:{data.agent_name}", str(task.id))

    return task


@router.get("/tasks/{task_id}", response_model=AITaskResponse,
            dependencies=[Depends(require_permission("ai_tasks", "read"))])
async def get_ai_task(task_id: UUID, db: AsyncSession = Depends(get_db)):
    """Check status and result of an AI task."""
    task = await db.get(AITask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/tasks",
            dependencies=[Depends(require_permission("ai_tasks", "read"))])
async def list_tasks(
    status: str | None = None,
    agent_name: str | None = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """List recent AI tasks."""
    query = select(AITask).order_by(AITask.created_at.desc()).limit(limit)
    if status:
        query = query.where(AITask.status == status)
    if agent_name:
        query = query.where(AITask.agent_name == agent_name)
    result = await db.execute(query)
    return result.scalars().all()
