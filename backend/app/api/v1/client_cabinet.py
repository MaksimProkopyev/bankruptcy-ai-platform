"""Client cabinet API — 'one window' for bankruptcy clients.

Clients see ONLY their own data. Every endpoint is scoped to client_id.
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.session import get_db
from app.models.models import (
    Case,
    CaseEvent,
    Client,
    Document,
    DocumentStatus,
    DocumentType,
    Notification,
)
from app.services.file_storage import get_storage

router = APIRouter()
security = HTTPBearer()


async def get_current_client(
    creds: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Client:
    try:
        payload = jwt.decode(creds.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    if payload.get("scope") != "client":
        raise HTTPException(status_code=403, detail="Not a client token")
    client = await db.get(Client, UUID(payload["sub"]))
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


async def _get_active_case(client: Client, db: AsyncSession):
    query = (
        select(Case)
        .options(
            selectinload(Case.creditors),
            selectinload(Case.deadlines),
            selectinload(Case.documents),
            selectinload(Case.payments),
            selectinload(Case.lawyer),
        )
        .where(Case.client_id == client.id)
        .where(Case.status.notin_(["rejected", "cancelled"]))
        .order_by(Case.created_at.desc())
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


STAGE_INFO = {
    "lead": {
        "label": "Заявка принята",
        "description": "Мы получили вашу заявку.",
        "what_now": "Специалист свяжется для уточнений.",
        "what_next": "Консультация с юристом",
        "client_action": None,
    },
    "qualification": {
        "label": "Оценка ситуации",
        "description": "AI анализирует ваши данные.",
        "what_now": "Автоматическая проверка.",
        "what_next": "Консультация",
        "client_action": None,
    },
    "consultation": {
        "label": "Консультация с юристом",
        "description": "Юрист подбирает стратегию.",
        "what_now": "Готовятся рекомендации.",
        "what_next": "Подписание договора",
        "client_action": "Будьте на связи.",
    },
    "contract_signing": {
        "label": "Подписание договора",
        "description": "Оформляем договор.",
        "what_now": "Договор готовится.",
        "what_next": "Сбор документов",
        "client_action": "Подпишите договор и внесите первый платёж.",
    },
    "document_collection": {
        "label": "Сбор документов",
        "description": "Собираем документы для суда.",
        "what_now": "Проверьте раздел «Документы».",
        "what_next": "Проверка и подготовка заявления",
        "client_action": "Загрузите недостающие документы.",
    },
    "document_review": {
        "label": "Проверка документов",
        "description": "AI и юрист проверяют документы.",
        "what_now": "Идёт проверка.",
        "what_next": "Подготовка заявления",
        "client_action": None,
    },
    "application_preparation": {
        "label": "Подготовка заявления",
        "description": "AI генерирует заявление, юрист проверяет.",
        "what_now": "Готовим пакет для суда.",
        "what_next": "Подача в суд",
        "client_action": None,
    },
    "application_filed": {
        "label": "Заявление подано",
        "description": "Заявление подано в арбитражный суд.",
        "what_now": "Суд рассматривает (5 дней).",
        "what_next": "Назначение заседания",
        "client_action": "Ожидайте.",
    },
    "court_accepted": {
        "label": "Суд принял заявление",
        "description": "Заявление принято к производству.",
        "what_now": "Назначается заседание и ФУ.",
        "what_next": "Первое заседание",
        "client_action": None,
    },
    "hearing_scheduled": {
        "label": "Заседание назначено",
        "description": "Назначена дата заседания.",
        "what_now": "Юрист готовится. Ваше присутствие не требуется.",
        "what_next": "Введение процедуры",
        "client_action": None,
    },
    "procedure_started": {
        "label": "Процедура введена",
        "description": "Суд ввёл процедуру. Кредиторы больше не могут предъявлять требования напрямую.",
        "what_now": "Формируется реестр кредиторов.",
        "what_next": "Реализация → списание долгов",
        "client_action": "Сотрудничайте с финансовым управляющим.",
    },
    "creditors_registry": {
        "label": "Реестр кредиторов",
        "description": "Кредиторы подают требования.",
        "what_now": "Юрист проверяет обоснованность.",
        "what_next": "Собрание кредиторов",
        "client_action": None,
    },
    "creditors_meeting": {
        "label": "Собрание кредиторов",
        "description": "Кредиторы голосуют.",
        "what_now": "Проводится собрание.",
        "what_next": "Реализация имущества",
        "client_action": None,
    },
    "asset_realization": {
        "label": "Реализация имущества",
        "description": "ФУ формирует конкурсную массу. Единственное жильё защищено.",
        "what_now": "Процедура 6 месяцев.",
        "what_next": "Отчёт ФУ → списание",
        "client_action": "Отвечайте на запросы ФУ.",
    },
    "restructuring": {
        "label": "Реструктуризация",
        "description": "Утверждён план погашения до 3 лет.",
        "what_now": "Выплаты по графику.",
        "what_next": "Завершение",
        "client_action": "Вносите платежи по графику.",
    },
    "fu_report": {
        "label": "Отчёт ФУ",
        "description": "ФУ подготовил отчёт для суда.",
        "what_now": "Суд рассматривает.",
        "what_next": "Завершение процедуры",
        "client_action": None,
    },
    "completion": {
        "label": "Завершение",
        "description": "Суд завершает процедуру.",
        "what_now": "Решение об освобождении.",
        "what_next": "Списание долгов",
        "client_action": None,
    },
    "debt_discharged": {
        "label": "Долги списаны!",
        "description": "Поздравляем! Вы свободны от долгов. Процедура завершена.",
        "what_now": "Вы свободны от долгов.",
        "what_next": None,
        "client_action": None,
    },
}

STATUS_ORDER = list(STAGE_INFO.keys())


@router.get("/me")
async def get_profile(client: Client = Depends(get_current_client)):
    return {
        "id": str(client.id),
        "first_name": client.first_name,
        "last_name": client.last_name,
        "phone": client.phone,
        "email": client.email,
    }


@router.get("/case")
async def get_case_overview(client: Client = Depends(get_current_client), db: AsyncSession = Depends(get_db)):
    case = await _get_active_case(client, db)
    if not case:
        return {"has_case": False}

    idx = STATUS_ORDER.index(case.status) if case.status in STATUS_ORDER else 0
    progress = round(idx / (len(STATUS_ORDER) - 1) * 100)
    stage = STAGE_INFO.get(case.status, {})

    pending_deadlines = sorted([d for d in case.deadlines if d.status == "pending"], key=lambda d: d.due_date)[:3]

    from app.services.document_checklist import calculate_completeness, get_required_documents

    checklist = get_required_documents(
        marital_status=client.marital_status, is_employed=client.is_employed, creditors_count=len(case.creditors)
    )
    collected = {
        doc.document_type.value if hasattr(doc.document_type, "value") else doc.document_type
        for doc in case.documents
        if doc.status not in ("pending", "rejected")
    }
    doc_prog = calculate_completeness(checklist, collected)

    lawyer_info = None
    if case.lawyer:
        lawyer_info = {
            "name": f"{case.lawyer.last_name} {case.lawyer.first_name}",
            "email": case.lawyer.email,
            "phone": case.lawyer.phone,
        }

    return {
        "has_case": True,
        "case_number": case.case_number,
        "status": case.status,
        "progress_percent": progress,
        "stage": {
            "label": stage.get("label", ""),
            "description": stage.get("description", ""),
            "what_now": stage.get("what_now", ""),
            "what_next": stage.get("what_next"),
            "client_action": stage.get("client_action"),
        },
        "completed_stages": [{"key": s, "label": STAGE_INFO[s]["label"]} for s in STATUS_ORDER[:idx]],
        "current_stage_index": idx,
        "total_stages": len(STATUS_ORDER),
        "total_debt": float(case.total_debt) if case.total_debt else None,
        "creditors_count": len(case.creditors),
        "court_name": case.court_name,
        "court_case_number": case.court_case_number,
        "next_hearing": case.first_hearing_date.isoformat() if case.first_hearing_date else None,
        "upcoming_deadlines": [
            {"title": d.title, "due_date": d.due_date.isoformat(), "priority": d.priority} for d in pending_deadlines
        ],
        "documents_progress": doc_prog["progress_percent"],
        "documents_missing": doc_prog["missing"],
        "lawyer": lawyer_info,
        "financial_manager": case.financial_manager_name,
    }


@router.get("/creditors")
async def get_my_creditors(client: Client = Depends(get_current_client), db: AsyncSession = Depends(get_db)):
    case = await _get_active_case(client, db)
    if not case:
        return {"creditors": [], "summary": {"total_debt": 0, "count": 0}}

    creds = [
        {
            "name": c.name,
            "type": c.creditor_type,
            "total_amount": float(c.total_amount),
            "principal": float(c.principal_amount) if c.principal_amount else None,
            "interest": float(c.interest_amount) if c.interest_amount else None,
            "penalty": float(c.penalty_amount) if c.penalty_amount else None,
            "is_secured": c.is_secured,
            "in_registry": c.included_in_registry,
            "contract_number": c.contract_number,
        }
        for c in case.creditors
    ]
    total = sum(c["total_amount"] for c in creds)
    return {
        "creditors": creds,
        "summary": {
            "total_debt": total,
            "secured_debt": sum(c["total_amount"] for c in creds if c["is_secured"]),
            "unsecured_debt": sum(c["total_amount"] for c in creds if not c["is_secured"]),
            "count": len(creds),
            "in_registry": sum(1 for c in creds if c["in_registry"]),
        },
    }


@router.get("/events")
async def get_my_events(client: Client = Depends(get_current_client), db: AsyncSession = Depends(get_db)):
    case = await _get_active_case(client, db)
    if not case:
        return []
    result = await db.execute(
        select(CaseEvent)
        .where(CaseEvent.case_id == case.id, CaseEvent.is_visible_to_client)
        .order_by(CaseEvent.created_at.desc())
        .limit(30)
    )
    return [
        {"title": e.title, "description": e.description, "date": e.created_at.isoformat(), "type": e.event_type}
        for e in result.scalars().all()
    ]


@router.get("/documents")
async def get_my_documents(client: Client = Depends(get_current_client), db: AsyncSession = Depends(get_db)):
    from app.services.document_checklist import calculate_completeness, get_required_documents

    case = await _get_active_case(client, db)
    if not case:
        return {"checklist": [], "progress_percent": 0}
    checklist = get_required_documents(
        marital_status=client.marital_status, is_employed=client.is_employed, creditors_count=len(case.creditors)
    )
    collected = {
        doc.document_type.value if hasattr(doc.document_type, "value") else doc.document_type
        for doc in case.documents
        if doc.status not in ("pending", "rejected")
    }
    progress = calculate_completeness(checklist, collected)
    return {
        "checklist": [
            {**item, "is_collected": item["type"] in collected} for item in checklist if item["category"] != "process"
        ],
        **progress,
    }


@router.post("/documents/upload")
async def client_upload_document(
    document_type: str = Form(...),
    file: UploadFile = File(...),
    client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    case = await _get_active_case(client, db)
    if not case:
        raise HTTPException(status_code=404, detail="No active case")
    file_data = await file.read()
    if len(file_data) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Max 20MB")
    try:
        doc_type = DocumentType(document_type)
    except ValueError:
        doc_type = DocumentType.other
    storage = get_storage()
    s3 = storage.upload_file(
        file_data=file_data,
        file_name=file.filename or "doc",
        case_id=str(case.id),
        content_type=file.content_type or "application/octet-stream",
    )
    doc = Document(
        case_id=case.id,
        document_type=doc_type,
        status=DocumentStatus.uploaded,
        file_name=s3["file_name"],
        file_path=s3["file_path"],
        file_size=s3["file_size"],
        mime_type=s3["mime_type"],
        uploaded_by_client=True,
    )
    db.add(doc)
    db.add(
        CaseEvent(
            case_id=case.id,
            event_type="document_uploaded",
            title=f"Клиент загрузил: {file.filename}",
            is_system_event=True,
            is_visible_to_client=True,
        )
    )
    await db.commit()
    return {"message": "Документ загружен", "document_id": str(doc.id)}


@router.get("/payments")
async def get_my_payments(client: Client = Depends(get_current_client), db: AsyncSession = Depends(get_db)):
    case = await _get_active_case(client, db)
    if not case:
        return {"payments": [], "total_paid": 0, "total_pending": 0, "cost_breakdown": {}}
    payments = [
        {
            "id": str(p.id),
            "payment_type": p.payment_type,
            "amount": float(p.amount),
            "status": p.status,
            "due_date": p.due_date.isoformat() if p.due_date else None,
            "paid_date": p.paid_date.isoformat() if p.paid_date else None,
            "invoice_number": p.invoice_number,
        }
        for p in case.payments
    ]
    return {
        "payments": payments,
        "total_paid": sum(p["amount"] for p in payments if p["status"] == "paid"),
        "total_pending": sum(p["amount"] for p in payments if p["status"] in ("pending", "overdue")),
        "cost_breakdown": {
            "service_fee": float(case.service_fee or 0),
            "court_fee": 300,
            "fu_deposit": 25000,
            "publications": 15000,
            "total_estimated": float(case.service_fee or 80000) + 40300,
        },
    }


@router.get("/lawyer")
async def get_my_lawyer(client: Client = Depends(get_current_client), db: AsyncSession = Depends(get_db)):
    case = await _get_active_case(client, db)
    if not case or not case.lawyer:
        return {"assigned": False, "message": "Юрист будет назначен после подписания договора"}
    return {
        "assigned": True,
        "name": f"{case.lawyer.last_name} {case.lawyer.first_name} {case.lawyer.patronymic or ''}".strip(),
        "email": case.lawyer.email,
        "phone": case.lawyer.phone,
        "role": "Юрист по банкротству",
    }


class ConsultationRequest(BaseModel):
    preferred_date: str
    preferred_time: str
    topic: str


@router.post("/consultation")
async def book_consultation_legacy(
    data: ConsultationRequest, client: Client = Depends(get_current_client), db: AsyncSession = Depends(get_db)
):
    case = await _get_active_case(client, db)
    db.add(
        CaseEvent(
            case_id=case.id if case else None,
            event_type="client_message",
            title=f"Запрос на консультацию: {data.topic}",
            description=f"Дата: {data.preferred_date}, время: {data.preferred_time}",
            is_visible_to_client=True,
            is_system_event=True,
        )
    )
    if case and case.assigned_lawyer_id:
        db.add(
            Notification(
                user_id=case.assigned_lawyer_id,
                case_id=case.id,
                title=f"Запрос на консультацию от {client.last_name}",
                body=f"Тема: {data.topic}, {data.preferred_date} {data.preferred_time}",
            )
        )
    await db.commit()
    return {"message": "Запрос отправлен. Юрист свяжется для подтверждения."}


@router.get("/notifications")
async def get_my_notifications(client: Client = Depends(get_current_client), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Notification)
        .where(Notification.client_id == client.id)
        .order_by(Notification.created_at.desc())
        .limit(30)
    )
    notifs = result.scalars().all()
    return {
        "notifications": [
            {"id": str(n.id), "title": n.title, "body": n.body, "is_read": n.is_read, "date": n.created_at.isoformat()}
            for n in notifs
        ],
        "unread_count": sum(1 for n in notifs if not n.is_read),
    }


@router.post("/notifications/read-all")
async def mark_notifications_read(client: Client = Depends(get_current_client), db: AsyncSession = Depends(get_db)):
    await db.execute(
        update(Notification)
        .where(Notification.client_id == client.id, not Notification.is_read)
        .values(is_read=True, read_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return {"ok": True}


@router.post("/chat")
async def client_chat(message: str, client: Client = Depends(get_current_client), db: AsyncSession = Depends(get_db)):
    import httpx

    case = await _get_active_case(client, db)
    stage = STAGE_INFO.get(case.status, {}) if case else {}
    context = {
        "client_name": f"{client.first_name}",
        "case_number": case.case_number if case else None,
        "status_label": stage.get("label", ""),
        "total_debt": float(case.total_debt) if case and case.total_debt else None,
        "what_now": stage.get("what_now", ""),
        "what_next": stage.get("what_next", ""),
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as http:
            resp = await http.post(
                f"{settings.AI_CORE_URL}/chat",
                json={"messages": [{"role": "user", "content": message}], "context": context},
            )
            resp.raise_for_status()
            return {"reply": resp.json().get("reply", "")}
    except Exception:
        return {"reply": "Извините, сервис временно недоступен. Позвоните: 8 800 123-45-67."}


# ─── Consultations ───


class ConsultationBookRequest(BaseModel):
    scheduled_at: datetime
    consultation_type: str = "phone"
    topic: str | None = None


@router.get("/consultations")
async def get_consultations(client: Client = Depends(get_current_client), db: AsyncSession = Depends(get_db)):
    """List consultations: upcoming and past."""
    from app.models.cabinet_models import Consultation

    case = await _get_active_case(client, db)
    if not case:
        return {"upcoming": [], "past": []}

    result = await db.execute(
        select(Consultation).where(Consultation.case_id == case.id).order_by(Consultation.scheduled_at.desc())
    )
    now = datetime.now(timezone.utc)
    upcoming, past = [], []

    for c in result.scalars().all():
        item = {
            "id": str(c.id),
            "scheduled_at": c.scheduled_at.isoformat(),
            "duration_minutes": c.duration_minutes,
            "type": c.consultation_type,
            "status": c.status,
            "topic": c.topic,
            "meeting_url": c.meeting_url if c.status in ("scheduled", "confirmed") else None,
        }
        if c.scheduled_at > now and c.status in ("scheduled", "confirmed"):
            upcoming.append(item)
        else:
            item["lawyer_notes"] = c.lawyer_notes
            past.append(item)

    return {"upcoming": upcoming, "past": past}


@router.post("/consultations/book")
async def book_consultation(
    data: ConsultationBookRequest, client: Client = Depends(get_current_client), db: AsyncSession = Depends(get_db)
):
    """Book a consultation with the assigned lawyer."""
    from app.models.cabinet_models import Consultation

    case = await _get_active_case(client, db)
    if not case:
        raise HTTPException(status_code=404, detail="No active case")

    c = Consultation(
        case_id=case.id,
        client_id=client.id,
        lawyer_id=case.assigned_lawyer_id,
        scheduled_at=data.scheduled_at,
        consultation_type=data.consultation_type,
        topic=data.topic,
        status="scheduled",
    )
    db.add(c)

    if case.assigned_lawyer_id:
        db.add(
            Notification(
                user_id=case.assigned_lawyer_id,
                case_id=case.id,
                title=f"Клиент {client.last_name} записался на консультацию",
                body=data.scheduled_at.strftime("%d.%m %H:%M"),
            )
        )

    db.add(
        CaseEvent(
            case_id=case.id,
            event_type="system_event",
            title=f"Запись на консультацию: {data.scheduled_at.strftime('%d.%m.%Y %H:%M')}",
            is_system_event=True,
            is_visible_to_client=True,
        )
    )
    await db.commit()
    return {"message": "Консультация запланирована", "id": str(c.id)}


@router.post("/consultations/{consultation_id}/cancel")
async def cancel_consultation(
    consultation_id: UUID, client: Client = Depends(get_current_client), db: AsyncSession = Depends(get_db)
):
    from app.models.cabinet_models import Consultation

    c = await db.get(Consultation, consultation_id)
    if not c or c.client_id != client.id:
        raise HTTPException(status_code=404)
    if c.status not in ("scheduled", "confirmed"):
        raise HTTPException(status_code=400, detail="Cannot cancel")
    c.status = "cancelled"
    await db.commit()
    return {"message": "Отменено"}


# ─── Calendar (unified) ───


@router.get("/calendar")
async def get_calendar(client: Client = Depends(get_current_client), db: AsyncSession = Depends(get_db)):
    """Unified calendar: hearings, deadlines, consultations."""
    from app.models.cabinet_models import Consultation

    case = await _get_active_case(client, db)
    if not case:
        return []

    events = []
    if case.first_hearing_date:
        events.append(
            {
                "type": "hearing",
                "title": "Судебное заседание",
                "date": case.first_hearing_date.isoformat(),
                "location": case.court_name,
                "icon": "🏛",
            }
        )

    for d in case.deadlines:
        if d.status == "pending" and d.due_date:
            events.append(
                {
                    "type": "deadline",
                    "title": d.title,
                    "date": d.due_date.isoformat(),
                    "priority": d.priority,
                    "icon": "⏰",
                }
            )

    result = await db.execute(
        select(Consultation).where(Consultation.case_id == case.id, Consultation.status.in_(["scheduled", "confirmed"]))
    )
    for c in result.scalars().all():
        events.append(
            {
                "type": "consultation",
                "title": f"Консультация ({c.consultation_type})",
                "date": c.scheduled_at.isoformat(),
                "duration_minutes": c.duration_minutes,
                "meeting_url": c.meeting_url,
                "icon": "📞",
            }
        )

    events.sort(key=lambda e: e["date"])
    return events


# ─── Messages (two-way) ───


@router.get("/messages")
async def get_messages(
    client: Client = Depends(get_current_client), db: AsyncSession = Depends(get_db), limit: int = 50
):
    """Two-way messages between client and staff."""
    from app.models.models import Message

    case = await _get_active_case(client, db)
    if not case:
        return []

    result = await db.execute(
        select(Message).where(Message.case_id == case.id).order_by(Message.created_at.asc()).limit(limit)
    )
    return [
        {
            "id": str(m.id),
            "direction": m.direction,
            "content": m.content,
            "is_ai": m.is_ai_generated,
            "date": m.created_at.isoformat(),
        }
        for m in result.scalars().all()
    ]


@router.post("/messages")
async def send_message_to_staff(
    data: dict, client: Client = Depends(get_current_client), db: AsyncSession = Depends(get_db)
):
    """Client sends a message to their legal team."""
    from app.models.models import Message

    case = await _get_active_case(client, db)
    if not case:
        raise HTTPException(status_code=404)

    content = data.get("content", "")
    if not content:
        raise HTTPException(status_code=400, detail="Message content required")

    msg = Message(case_id=case.id, client_id=client.id, channel="chat", direction="inbound", content=content)
    db.add(msg)

    if case.assigned_lawyer_id:
        db.add(
            Notification(
                user_id=case.assigned_lawyer_id,
                case_id=case.id,
                title=f"Сообщение от {client.last_name}",
                body=content[:100],
            )
        )

    await db.commit()
    return {"message": "Отправлено", "id": str(msg.id)}


# ─── Document Signing (client side) ───


@router.get("/signing/pending")
async def get_pending_signatures(client: Client = Depends(get_current_client), db: AsyncSession = Depends(get_db)):
    """Get documents waiting for client's signature."""
    from app.models.billing_models import DocumentDraft

    case = await _get_active_case(client, db)
    if not case:
        return []

    result = await db.execute(
        select(DocumentDraft)
        .where(DocumentDraft.case_id == case.id, DocumentDraft.status == "sent_for_signing")
        .order_by(DocumentDraft.created_at.desc())
    )
    return [
        {
            "id": str(d.id),
            "title": d.title,
            "status": d.status,
            "created_at": d.created_at.isoformat(),
            "content_preview": d.content_html[:300] + "..." if len(d.content_html) > 300 else d.content_html,
        }
        for d in result.scalars().all()
    ]


@router.post("/signing/request-code")
async def request_signing_code_legacy(
    draft_id: str, client: Client = Depends(get_current_client), db: AsyncSession = Depends(get_db)
):
    """Request SMS code to sign a document."""
    from app.services.esign_service import ESignService

    svc = ESignService(db)
    try:
        sig = await svc.initiate_signing(UUID(draft_id), client.id)
        await db.commit()
        return {
            "signature_id": str(sig.id),
            "phone_masked": client.phone[:4] + "***" + client.phone[-2:],
            "expires_in_minutes": 10,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/signing/verify")
async def verify_signing_code_legacy(
    signature_id: str,
    code: str,
    client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    """Verify SMS code and sign the document."""
    from app.services.esign_service import ESignService

    svc = ESignService(db)
    try:
        sig = await svc.verify_and_sign(
            signature_id=UUID(signature_id),
            code=code,
        )
        await db.commit()
        return {"status": "signed", "signed_at": sig.signed_at.isoformat() if sig.signed_at else None}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/invoices-legacy")
async def get_my_invoices_legacy(client: Client = Depends(get_current_client), db: AsyncSession = Depends(get_db)):
    """Get invoices for client's case with payment links."""
    from app.models.billing_models import Invoice

    case = await _get_active_case(client, db)
    if not case:
        return []

    result = await db.execute(select(Invoice).where(Invoice.case_id == case.id).order_by(Invoice.created_at.desc()))
    return [
        {
            "id": str(i.id),
            "number": i.invoice_number,
            "amount": float(i.total_amount),
            "status": i.status,
            "due_date": i.due_date.isoformat() if i.due_date else None,
            "payment_url": i.payment_url,
            "paid_at": i.paid_at.isoformat() if i.paid_at else None,
        }
        for i in result.scalars().all()
    ]


# ─── Document signing (e-signature) ───


@router.get("/documents-to-sign")
async def get_documents_to_sign(client: Client = Depends(get_current_client), db: AsyncSession = Depends(get_db)):
    """List documents awaiting client's signature."""
    from app.models.billing_models import DocumentDraft

    case = await _get_active_case(client, db)
    if not case:
        return {"documents": []}

    result = await db.execute(
        select(DocumentDraft)
        .where(
            DocumentDraft.case_id == case.id,
            DocumentDraft.status == "sent_for_signing",
            DocumentDraft.requires_client_signature,
        )
        .order_by(DocumentDraft.created_at.desc())
    )
    drafts = result.scalars().all()

    return {
        "documents": [
            {
                "id": str(d.id),
                "title": d.title,
                "status": d.status,
                "created_at": d.created_at.isoformat() if d.created_at else None,
                "file_path": d.file_path,
            }
            for d in drafts
        ]
    }


@router.post("/sign/request-code")
async def request_signing_code(
    draft_id: str,
    client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    """Request SMS code to sign a document."""
    from app.models.billing_models import DocumentDraft
    from app.services.esign_service import ESignService

    draft = await db.get(DocumentDraft, UUID(draft_id))
    if not draft:
        raise HTTPException(status_code=404, detail="Document not found")

    # Verify this document belongs to client's case
    case = await _get_active_case(client, db)
    if not case or draft.case_id != case.id:
        raise HTTPException(status_code=403, detail="Access denied")

    esign = ESignService(db)
    signature = await esign.initiate_signing(
        client_id=client.id,
        case_id=case.id,
        draft_id=UUID(draft_id),
        document_title=draft.title,
        document_hash=draft.file_hash or "",
        phone=client.phone,
    )
    await db.commit()

    return {
        "signature_id": str(signature.id),
        "message": f"Код отправлен на {client.phone}",
        "expires_in": 300,
    }


@router.post("/sign/verify")
async def verify_signing_code(
    signature_id: str,
    code: str,
    client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    """Verify SMS code and complete document signing."""
    from app.services.esign_service import ESignService

    esign = ESignService(db)
    result = await esign.verify_and_sign(
        signature_id=UUID(signature_id),
        code=code,
        ip_address="",  # TODO: extract from request
        user_agent="",
    )
    await db.commit()

    if result.get("success"):
        # Notify lawyer
        case = await _get_active_case(client, db)
        if case and case.assigned_lawyer_id:
            db.add(
                Notification(
                    user_id=case.assigned_lawyer_id,
                    case_id=case.id,
                    title=f"Клиент {client.last_name} подписал документ",
                    body=result.get("document_title", ""),
                )
            )
        db.add(
            CaseEvent(
                case_id=case.id if case else None,
                event_type="system_event",
                title=f"Документ подписан клиентом: {result.get('document_title', '')}",
                is_system_event=True,
                is_visible_to_client=True,
            )
        )
        await db.commit()

    return result


@router.get("/invoices")
async def get_my_invoices(client: Client = Depends(get_current_client), db: AsyncSession = Depends(get_db)):
    """List invoices for client's case."""
    from app.models.billing_models import Invoice

    case = await _get_active_case(client, db)
    if not case:
        return {"invoices": []}

    result = await db.execute(select(Invoice).where(Invoice.case_id == case.id).order_by(Invoice.invoice_date.desc()))
    invoices = result.scalars().all()

    return {
        "invoices": [
            {
                "id": str(inv.id),
                "number": inv.invoice_number,
                "date": inv.invoice_date.isoformat() if inv.invoice_date else None,
                "due_date": inv.due_date.isoformat() if inv.due_date else None,
                "total_amount": float(inv.total_amount),
                "status": inv.status,
                "payment_url": inv.payment_url,
                "items": inv.items or [],
            }
            for inv in invoices
        ]
    }
