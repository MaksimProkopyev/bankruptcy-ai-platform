"""Anticollector API — call blocking, collector database, lead generation.

The Anticollector is a FREE utility app that:
1. Blocks calls from known collector numbers
2. Blocks all unknown numbers (not in contacts)
3. Records collector call attempts (evidence for court)
4. Analyzes SMS from collectors (detects threats/violations)
5. Provides legal tips
6. AUTO-GENERATES leads: every registered user is a warm lead

This is a leadgen trojan horse — users install it for protection,
we get their phone number + proof they have debt problems.
"""

from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.models import Client, Case, CaseEvent, Notification

router = APIRouter()


# ─── Schemas ─────────────────────────────────────────────────

class AnticollectorRegister(BaseModel):
    phone: str
    device_os: str = "android"  # android | ios
    app_version: str = "1.0.0"
    push_token: Optional[str] = None


class AnticollectorRegisterResponse(BaseModel):
    user_id: str
    blocked_numbers_count: int
    message: str


class BlockedNumberReport(BaseModel):
    phone_number: str
    collector_name: Optional[str] = None
    call_count: int = 1
    is_threatening: bool = False
    notes: Optional[str] = None


class CallLogEntry(BaseModel):
    caller_number: str
    call_type: str = "blocked"  # blocked, answered, missed
    duration_seconds: int = 0
    was_recorded: bool = False
    recording_path: Optional[str] = None


class SMSAnalysisRequest(BaseModel):
    sender: str
    text: str


class SMSAnalysisResponse(BaseModel):
    is_collector: bool
    threat_level: str  # none, mild, moderate, severe
    violations: list[str]
    legal_advice: str
    suggested_action: str


# ─── In-memory collector database (move to DB in production) ──

KNOWN_COLLECTORS = {
    "+74951234567": "Национальная служба взыскания",
    "+74959876543": "Первое коллекторское бюро",
    "+74957654321": "ЭОС",
    "+74953456789": "Сентинел Кредит Менеджмент",
    "+74952345678": "Филберт",
    "+74956543210": "АктивБизнесКонсалт",
    "+74951112233": "Кредитэкспресс Финанс",
    "+74954445566": "Столичное АВД",
    "+74957778899": "М.Б.А. Финансы",
    "+74950001122": "Югорское коллекторское агентство",
}

# Patterns indicating collector SMS
COLLECTOR_SMS_PATTERNS = [
    "задолженность", "долг", "просрочка", "взыскание", "оплатите",
    "судебный приказ", "исполнительное производство", "пристав",
    "коллектор", "цессия", "уступка права требования",
]

THREAT_PATTERNS = [
    "уголовная ответственность", "арест имущества", "выезд по адресу",
    "опись имущества", "принудительное взыскание", "сообщим работодателю",
    "сообщим родственникам", "ограничение выезда",
]


# ─── Endpoints ───────────────────────────────────────────────

@router.post("/register", response_model=AnticollectorRegisterResponse)
async def register_anticollector_user(
    data: AnticollectorRegister,
    db: AsyncSession = Depends(get_db),
):
    """Register new Anticollector user.
    
    This is the LEADGEN entry point:
    - User installs free app → registers with phone
    - Phone auto-becomes a warm lead in CRM
    - They clearly have debt problems (why else install anticollector?)
    """
    phone = data.phone.strip()

    # Check if client already exists
    result = await db.execute(select(Client).where(Client.phone == phone))
    client = result.scalar_one_or_none()

    if not client:
        # Create new client (lead)
        client = Client(
            first_name="",  # Will be filled during qualification
            last_name="Anticollector User",
            phone=phone,
            lead_source="anticollector_app",
            utm_source="anticollector",
            utm_medium="app",
        )
        db.add(client)
        await db.flush()

        # Auto-create a lead case
        case = Case(
            client_id=client.id,
            status="lead",
            notes=f"Лид из приложения Антиколлектор. Устройство: {data.device_os}, версия: {data.app_version}",
            tags=["anticollector", "auto_lead"],
        )
        db.add(case)

        event = CaseEvent(
            case_id=case.id,
            event_type="system_event",
            title="Лид из Антиколлектора",
            description=f"Пользователь установил Антиколлектор. Телефон: {phone}. ОС: {data.device_os}",
            is_system_event=True,
        )
        db.add(event)

        await db.commit()

    return AnticollectorRegisterResponse(
        user_id=str(client.id),
        blocked_numbers_count=len(KNOWN_COLLECTORS),
        message="Защита активирована. Звонки от коллекторов будут блокироваться.",
    )


@router.get("/blocked-numbers")
async def get_blocked_numbers(
    since_version: int = Query(0, description="Last known version for incremental sync"),
):
    """Get list of known collector phone numbers.
    
    App syncs this list periodically to block incoming calls.
    """
    numbers = [
        {"phone": phone, "name": name, "category": "collector"}
        for phone, name in KNOWN_COLLECTORS.items()
    ]

    return {
        "version": 1,
        "count": len(numbers),
        "numbers": numbers,
    }


@router.post("/report-number")
async def report_collector_number(
    data: BlockedNumberReport,
    db: AsyncSession = Depends(get_db),
):
    """User reports a new collector number.
    
    Crowdsourced collector database — if enough users report
    the same number, it gets added to the global block list.
    """
    # In production: save to reported_numbers table, 
    # add to global list after N reports
    return {
        "message": "Спасибо! Номер добавлен в базу.",
        "phone": data.phone_number,
    }


@router.post("/log-call")
async def log_blocked_call(
    data: CallLogEntry,
    phone: str = Query(..., description="User's phone"),
    db: AsyncSession = Depends(get_db),
):
    """Log a blocked/recorded collector call.
    
    Builds evidence trail for potential court proceedings.
    """
    # Find client
    result = await db.execute(select(Client).where(Client.phone == phone))
    client = result.scalar_one_or_none()

    if client:
        # Find their case
        case_result = await db.execute(
            select(Case).where(Case.client_id == client.id).order_by(Case.created_at.desc())
        )
        case = case_result.scalar_one_or_none()

        if case:
            collector_name = KNOWN_COLLECTORS.get(data.caller_number, "Неизвестный")
            event = CaseEvent(
                case_id=case.id,
                event_type="system_event",
                title=f"Заблокирован звонок: {collector_name}",
                description=f"Номер: {data.caller_number}, тип: {data.call_type}",
                event_metadata={
                    "caller": data.caller_number,
                    "collector_name": collector_name,
                    "call_type": data.call_type,
                    "duration": data.duration_seconds,
                    "recorded": data.was_recorded,
                },
                is_system_event=True,
            )
            db.add(event)
            await db.commit()

    return {"logged": True}


@router.post("/analyze-sms", response_model=SMSAnalysisResponse)
async def analyze_collector_sms(data: SMSAnalysisRequest):
    """AI analysis of SMS from collectors.
    
    Detects threats, legal violations, and provides advice.
    In production: calls Claude API for deep analysis.
    """
    text_lower = data.text.lower()

    # Check if it's from a collector
    is_collector = any(p in text_lower for p in COLLECTOR_SMS_PATTERNS)

    # Check for threats
    violations = []
    threat_level = "none"

    if any(p in text_lower for p in THREAT_PATTERNS):
        threat_level = "severe"
        if "уголовная" in text_lower:
            violations.append("Угроза уголовным преследованием (незаконно для гражданских долгов)")
        if "работодател" in text_lower:
            violations.append("Угроза сообщить работодателю (нарушение ФЗ-230)")
        if "родственник" in text_lower:
            violations.append("Угроза сообщить родственникам (нарушение ФЗ-230)")
        if "выезд" in text_lower or "опись" in text_lower:
            violations.append("Угроза описью имущества (только судебные приставы имеют право)")
    elif is_collector:
        threat_level = "mild"

    # Legal advice
    if threat_level == "severe":
        advice = "Это сообщение содержит признаки нарушения ФЗ-230. Коллектор не имеет права угрожать. Рекомендуем сохранить это SMS как доказательство и обратиться в ФССП с жалобой."
        action = "Сохраните SMS, подайте жалобу в ФССП. Рассмотрите банкротство для полного списания долга."
    elif is_collector:
        advice = "Типичное коллекторское уведомление. По закону коллекторы могут связываться не чаще 2 раз в неделю (ФЗ-230)."
        action = "Если звонки слишком частые, фиксируйте и подавайте жалобу."
    else:
        advice = "Это сообщение не похоже на коллекторское."
        action = "Нет необходимости в действиях."

    return SMSAnalysisResponse(
        is_collector=is_collector,
        threat_level=threat_level,
        violations=violations,
        legal_advice=advice,
        suggested_action=action,
    )


@router.get("/legal-tips")
async def get_legal_tips():
    """Legal tips for dealing with collectors."""
    return {
        "tips": [
            {
                "title": "Коллекторы не имеют права угрожать",
                "text": "По ФЗ-230 коллекторы не могут угрожать физическим насилием, уголовным преследованием или порчей имущества. Это административное правонарушение.",
                "law": "ФЗ-230, ст. 6",
            },
            {
                "title": "Ограничения на звонки",
                "text": "Коллекторы могут звонить не чаще 1 раза в сутки, 2 раз в неделю и 8 раз в месяц. Звонки разрешены только с 8:00 до 22:00 в будни и с 9:00 до 20:00 в выходные.",
                "law": "ФЗ-230, ст. 7",
            },
            {
                "title": "Право отказаться от общения",
                "text": "Вы можете написать заявление об отказе от взаимодействия. После этого коллектор может обращаться только через суд.",
                "law": "ФЗ-230, ст. 8",
            },
            {
                "title": "Банкротство останавливает коллекторов",
                "text": "После подачи заявления о банкротстве вводится мораторий — все требования кредиторов прекращаются, коллекторы не имеют права звонить.",
                "law": "ФЗ-127, ст. 213.11",
            },
            {
                "title": "Запишите звонок коллектора",
                "text": "Записи звонков — допустимое доказательство в суде. Фиксируйте дату, время, содержание разговора. Это поможет при подаче жалобы.",
                "law": "ГПК РФ, ст. 55",
            },
            {
                "title": "Куда жаловаться",
                "text": "Жалобы на коллекторов можно подать в ФССП (приставы), Центробанк (если кредитор — банк), Роспотребнадзор и прокуратуру.",
                "law": "ФЗ-230, ст. 18-19",
            },
        ],
    }


@router.get("/stats")
async def get_anticollector_stats(db: AsyncSession = Depends(get_db)):
    """Stats for the anticollector module (for CRM dashboard)."""
    # Total anticollector users (leads)
    total_users = await db.execute(
        select(func.count(Client.id)).where(Client.lead_source == "anticollector_app")
    )

    # Converted to cases
    converted = await db.execute(
        select(func.count(Case.id))
        .join(Client, Case.client_id == Client.id)
        .where(Client.lead_source == "anticollector_app")
        .where(Case.status.notin_(["lead", "rejected"]))
    )

    return {
        "total_users": total_users.scalar_one(),
        "converted_to_cases": converted.scalar_one(),
        "blocked_numbers_in_db": len(KNOWN_COLLECTORS),
        "conversion_rate": "TBD",
    }
