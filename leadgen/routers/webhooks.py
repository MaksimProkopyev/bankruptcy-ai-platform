import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from leadgen.adapters.web_form import WebFormAdapter
from leadgen.database import get_db
from leadgen.services import lead_service
from leadgen.services.agent_trigger import trigger_sales_agent

router = APIRouter()
logger = logging.getLogger(__name__)

_web_adapter = WebFormAdapter()


@router.post("/web-form")
async def web_form_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Принимает заявку с веб-формы сайта."""
    payload = await request.json()
    event = await _web_adapter.normalize(payload)
    lead = await lead_service.process_incoming_event(db, event)

    background_tasks.add_task(
        trigger_sales_agent,
        lead_id=str(lead.id),
        message_text=event.message,
        channel=str(event.channel.value),
        adapter=_web_adapter,
    )

    return {"lead_id": str(lead.id), "status": lead.status}


@router.post("/telegram")
async def telegram_webhook(request: Request) -> dict:
    """Принимает обновления от Telegram Bot API (обработка в следующем спринте)."""
    payload = await request.json()
    logger.info(f"Telegram webhook received: update_id={payload.get('update_id')}")
    return {"ok": True}


@router.post("/whatsapp")
async def whatsapp_webhook(request: Request) -> dict:
    """Принимает сообщения из WhatsApp (Green API / обработка в следующем спринте)."""
    payload = await request.json()
    logger.info(f"WhatsApp webhook received: {list(payload.keys())}")
    return {"ok": True}


@router.get("/whatsapp")
async def whatsapp_verify(request: Request) -> str:
    """Верификация webhook WhatsApp (hub.challenge)."""
    params = dict(request.query_params)
    return params.get("hub.challenge", "ok")


@router.post("/vk")
async def vk_webhook(request: Request) -> str:
    """Принимает события от VK Callback API (обработка в следующем спринте)."""
    payload = await request.json()
    logger.info(f"VK webhook received: type={payload.get('type')}")
    if payload.get("type") == "confirmation":
        return "ok"
    return "ok"


@router.post("/avito")
async def avito_webhook(request: Request) -> dict:
    """Принимает события из Avito (обработка в следующем спринте)."""
    payload = await request.json()
    logger.info(f"Avito webhook received: {list(payload.keys())}")
    return {"ok": True}


@router.post("/ok")
async def ok_webhook(request: Request) -> dict:
    """Принимает события от Одноклассников (обработка в следующем спринте)."""
    payload = await request.json()
    logger.info(f"OK webhook received: {list(payload.keys())}")
    return {"ok": True}


@router.post("/facebook")
async def facebook_webhook(request: Request) -> dict:
    """Принимает события от Facebook Messenger (обработка в следующем спринте)."""
    payload = await request.json()
    logger.info(f"Facebook webhook received: {list(payload.keys())}")
    return {"ok": True}


@router.get("/facebook")
async def facebook_verify(request: Request) -> str:
    """Верификация webhook Facebook."""
    params = dict(request.query_params)
    return params.get("hub.challenge", "ok")


@router.post("/max")
async def max_webhook(request: Request) -> dict:
    """Принимает события от MAX мессенджера (обработка в следующем спринте)."""
    payload = await request.json()
    logger.info(f"MAX webhook received: {list(payload.keys())}")
    return {"ok": True}
