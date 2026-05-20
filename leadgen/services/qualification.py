"""Qualification service — integrates leadgen with the LangGraph qualification agent.

Public API:
    start_qualification(lead_id, db)  → creates QualificationTask, starts graph in background
    resume_qualification(lead_id, new_message, db)  → resumes paused graph with new inbound message
"""

import asyncio
import logging
import os
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from leadgen.database import AsyncSessionLocal
from leadgen.models.lead import Lead, LeadStatus
from leadgen.models.lead_message import LeadMessage
from leadgen.models.prospect import Prospect, ProspectStatus
from leadgen.models.qualification_task import QualificationTask

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Graph singleton — built lazily on first use
# ---------------------------------------------------------------------------

_graph = None
_graph_lock: asyncio.Lock | None = None
_saver_ctx = None  # keep checkpointer context alive for process lifetime


def _get_lock() -> asyncio.Lock:
    global _graph_lock
    if _graph_lock is None:
        _graph_lock = asyncio.Lock()
    return _graph_lock


async def _get_graph():
    """Return (or lazily build) the compiled qualification graph."""
    global _graph, _saver_ctx

    if _graph is not None:
        return _graph

    async with _get_lock():
        if _graph is not None:
            return _graph

        from agents.qualification import build_qualification_graph

        checkpointer = None
        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

            db_url = os.getenv("DATABASE_URL", "")
            if db_url.startswith("postgresql+asyncpg://"):
                db_url = db_url.replace("postgresql+asyncpg://", "postgresql://", 1)

            if db_url:
                _saver_ctx = AsyncPostgresSaver.from_conn_string(db_url)
                checkpointer = await _saver_ctx.__aenter__()
                await checkpointer.setup()
                logger.info("qualification graph: Postgres checkpointer ready")
        except Exception as exc:
            logger.warning(
                "qualification graph: checkpointer unavailable (%s), running without persistence",
                exc,
            )

        _graph = await build_qualification_graph(checkpointer)
        logger.info("qualification graph: compiled (checkpointer=%s)", checkpointer is not None)
        return _graph


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def start_qualification(lead_id: UUID, db: AsyncSession) -> QualificationTask:
    """Create a QualificationTask and kick off the graph in the background.

    Uses the request db session for loading lead data and creating the task.
    The graph execution runs in a separate asyncio task with its own DB session.
    """
    lead = await db.get(Lead, lead_id)
    if not lead:
        raise ValueError(f"Lead {lead_id} not found")

    # Load recent messages to seed initial conversation context
    stmt = (
        select(LeadMessage)
        .where(LeadMessage.lead_id == lead_id)
        .order_by(LeadMessage.sent_at.asc())
        .limit(20)
    )
    recent_messages = (await db.execute(stmt)).scalars().all()

    # Create the task record in the current request session
    task = QualificationTask(lead_id=lead_id, status="processing")
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # Build LangChain messages from stored messages
    from langchain_core.messages import HumanMessage

    lc_messages = [
        HumanMessage(content=m.content)
        for m in recent_messages
        if m.direction == "inbound"
    ]

    initial_state = {
        "lead_id": str(lead_id),
        "channel": lead.channel or "web",
        "messages": lc_messages,
        "questions_queue": [],
        "gathered": {},
        "signals": {
            "debt_amount": float(lead.debt_amount) if lead.debt_amount else None,
            "debt_type": lead.debt_type,
            "has_property": lead.has_property,
            "has_income": lead.has_income,
        },
        "conflicts": [],
        "retry_count": 0,
        "escalation_level": 0,
        "score": None,
        "verdict": None,
        "reasoning": None,
        "interrupt_reason": None,
    }

    asyncio.create_task(
        _run_graph_background(str(task.id), str(lead_id), initial_state),
        name=f"qualify-{lead_id}",
    )

    return task


async def resume_qualification(lead_id: UUID, new_message: str, db: AsyncSession) -> None:
    """Resume the active qualification graph for a lead that just sent a new message.

    Looks up the active task using the request db session, then spawns
    a background asyncio task for the actual graph resumption.
    """
    stmt = (
        select(QualificationTask)
        .where(
            QualificationTask.lead_id == lead_id,
            QualificationTask.status == "processing",
        )
        .order_by(QualificationTask.created_at.desc())
    )
    task = (await db.execute(stmt)).scalar_one_or_none()

    if not task:
        logger.debug("resume_qualification: no active task for lead %s", lead_id)
        return

    asyncio.create_task(
        _resume_graph_background(str(task.id), str(lead_id), new_message),
        name=f"resume-{lead_id}",
    )


# ---------------------------------------------------------------------------
# Background runners (each creates its own DB session)
# ---------------------------------------------------------------------------


async def _run_graph_background(task_id: str, lead_id: str, initial_state: dict) -> None:
    """Run the graph from initial state; update DB on completion or failure."""
    try:
        graph = await _get_graph()
        config = {"configurable": {"thread_id": lead_id}}

        final_state = await graph.ainvoke(initial_state, config=config)
        await _handle_final_state(task_id, lead_id, final_state or {})
    except Exception:
        logger.exception("qualification graph failed for lead %s", lead_id)
        await _mark_task_failed(task_id, lead_id)


async def _resume_graph_background(task_id: str, lead_id: str, new_message: str) -> None:
    """Resume a paused graph with the lead's latest inbound message.

    Adds the new message to the checkpoint state via aupdate_state so that
    the wait_for_reply node sees a HumanMessage on the next tick.
    """
    try:
        from langchain_core.messages import HumanMessage

        graph = await _get_graph()
        config = {"configurable": {"thread_id": lead_id}}

        # Update state with the new inbound message, then resume
        await graph.aupdate_state(config, {"messages": [HumanMessage(content=new_message)]})
        final_state = await graph.ainvoke(None, config=config)
        await _handle_final_state(task_id, lead_id, final_state or {})
    except Exception:
        logger.exception("qualification graph resume failed for lead %s", lead_id)


async def _handle_final_state(task_id: str, lead_id: str, final_state: dict) -> None:
    """After ainvoke() returns, persist results if the graph completed."""
    verdict = final_state.get("verdict")
    terminal_verdicts = {"qualified", "disqualified", "archived"}

    if verdict not in terminal_verdicts:
        # Graph is still active (waiting for reply or soft-escalated)
        logger.info("qualification graph paused for lead %s (verdict=%s)", lead_id, verdict)
        return

    score = final_state.get("score")
    reasoning = final_state.get("reasoning") or ""
    signals = final_state.get("signals") or {}

    async with AsyncSessionLocal() as db:
        try:
            task = await db.get(QualificationTask, task_id)
            if task and task.status == "processing":
                task.status = "done"
                task.completed_at = datetime.utcnow()
                task.result = {
                    "score": score,
                    "reasoning": reasoning,
                    "verdict": verdict,
                    "signals": signals,
                }

            lead = await db.get(Lead, UUID(lead_id))
            if lead:
                if score is not None:
                    lead.qualification_score = score

                if verdict == "qualified":
                    lead.status = LeadStatus.QUALIFIED
                    existing = (
                        await db.execute(
                            select(Prospect).where(Prospect.lead_id == UUID(lead_id))
                        )
                    ).scalar_one_or_none()
                    if not existing:
                        db.add(
                            Prospect(
                                lead_id=UUID(lead_id),
                                status=ProspectStatus.PENDING,
                                qualification_data={
                                    "channel": lead.channel,
                                    "debt_amount": (
                                        float(lead.debt_amount) if lead.debt_amount else None
                                    ),
                                    "debt_type": lead.debt_type,
                                    "score": score,
                                    "reasoning": reasoning,
                                    "signals": signals,
                                },
                            )
                        )
                elif verdict == "disqualified":
                    lead.status = LeadStatus.DISQUALIFIED
                    lead.disqualify_reason = reasoning

            await db.commit()
            logger.info("qualification complete for lead %s: %s", lead_id, verdict)
        except Exception:
            logger.exception("DB update failed for lead %s after qualification", lead_id)
            await db.rollback()


async def _mark_task_failed(task_id: str, lead_id: str) -> None:
    """On graph exception: mark task failed and restore lead to 'new'."""
    async with AsyncSessionLocal() as db:
        try:
            task = await db.get(QualificationTask, task_id)
            if task:
                task.status = "failed"
                task.completed_at = datetime.utcnow()

            lead = await db.get(Lead, UUID(lead_id))
            if lead and lead.status == LeadStatus.IN_PROGRESS:
                lead.status = LeadStatus.NEW

            await db.commit()
        except Exception:
            logger.exception("failed to mark task %s as failed", task_id)


# ---------------------------------------------------------------------------
# Legacy stubs kept for backward compatibility
# ---------------------------------------------------------------------------


async def create_qualification_task(db: AsyncSession, lead: Lead) -> QualificationTask:
    task = QualificationTask(lead_id=lead.id, status="pending")
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def send_to_ai_studio(task_id: str, lead: Lead) -> None:
    """Deprecated — qualification is now handled directly by the LangGraph agent."""
    pass
