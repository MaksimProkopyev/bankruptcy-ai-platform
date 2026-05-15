"""Telegram bot for lead qualification and client communication.

Runs as a separate process alongside the main backend.
Usage: python -m integrations.telegram_bot

Two modes:
1. New users → qualification chatbot flow
2. Existing clients → case status, document upload, Q&A
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field

import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("telegram_bot")

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
AI_CORE_URL = os.environ.get("AI_CORE_URL", "http://localhost:8001")
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000/api/v1")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


@dataclass
class Session:
    chat_id: int
    messages: list = field(default_factory=list)
    session_id: str | None = None
    state: str = "idle"  # idle, qualifying, client


# In-memory session store (use Redis in production)
sessions: dict[int, Session] = {}


async def send_message(chat_id: int, text: str, reply_markup: dict | None = None):
    """Send a message to a Telegram chat."""
    async with httpx.AsyncClient() as client:
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup)
        await client.post(f"{TELEGRAM_API}/sendMessage", json=payload)


async def handle_start(chat_id: int):
    """Handle /start command."""
    sessions[chat_id] = Session(chat_id=chat_id, state="idle")

    await send_message(
        chat_id,
        "Здравствуйте! Я AI-консультант компании <b>Банкротство.AI</b>.\n\n"
        "Могу ответить на ваши вопросы о банкротстве физлиц, ИП, юрлиц и кредиторов.\n"
        "А также помочь:\n"
        "• Узнать, подходите ли вы под банкротство\n"
        "• Рассчитать стоимость процедуры\n"
        "• Проверить статус вашего дела\n\n"
        "Выберите действие или просто задайте вопрос:",
        reply_markup={
            "inline_keyboard": [
                [{"text": "❓ Задать вопрос о банкротстве", "callback_data": "ask_question"}],
                [{"text": "🔍 Проверить шансы на банкротство", "callback_data": "start_qualification"}],
                [{"text": "📋 Статус моего дела", "callback_data": "check_status"}],
                [{"text": "📞 Связаться с юристом", "callback_data": "contact_lawyer"}],
            ]
        },
    )


async def handle_callback(chat_id: int, callback_data: str):
    """Handle inline keyboard callbacks."""
    session = sessions.get(chat_id, Session(chat_id=chat_id))

    if callback_data == "ask_question":
        session.state = "idle"
        sessions[chat_id] = session
        await send_message(
            chat_id,
            "Отлично! Задайте ваш вопрос о банкротстве, и я постараюсь ответить на основе нашей базы знаний.\n\n"
            "Примеры вопросов:\n"
            "• Какие документы нужны для банкротства?\n"
            "• Сколько стоит банкротство для ИП?\n"
            "• Какие последствия у банкротства физлица?\n"
            "• Можно ли списать долги по кредитам?",
        )
        return

    if callback_data == "start_qualification":
        session.state = "qualifying"
        session.messages = []
        sessions[chat_id] = session

        # Send first message to AI to get greeting
        await process_qualification(chat_id, "Начать квалификацию")

    elif callback_data == "check_status":
        await send_message(
            chat_id, "Введите номер вашего дела (например, BK-2025-10001) или номер телефона, указанный при обращении:"
        )
        session.state = "client"
        sessions[chat_id] = session

    elif callback_data == "contact_lawyer":
        await send_message(
            chat_id,
            "📞 Позвоните нам: <b>8 800 123-45-67</b> (бесплатно)\n"
            "📧 Или напишите: info@bankruptcy.ai\n\n"
            "Юрист перезвонит в течение 15 минут в рабочее время (9:00–19:00 МСК).",
        )

    elif callback_data == "schedule_consultation":
        await send_message(
            chat_id,
            "Отлично! Для записи на бесплатную консультацию, пожалуйста, "
            "отправьте ваш номер телефона, и мы свяжемся с вами.",
        )


async def process_qualification(chat_id: int, user_text: str):
    """Forward message to AI Core chatbot and return response."""
    session = sessions.get(chat_id, Session(chat_id=chat_id))

    session.messages.append({"role": "user", "content": user_text})

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(
                f"{AI_CORE_URL}/chat",
                json={
                    "messages": session.messages,
                    "session_id": session.session_id,
                    "context": {"channel": "telegram", "chat_id": chat_id},
                },
            )
            data = res.json()

            session.session_id = data.get("session_id")
            session.messages.append({"role": "assistant", "content": data["reply"]})
            sessions[chat_id] = session

            await send_message(chat_id, data["reply"])

            # If qualification complete, show result and CTA
            if data.get("action") == "qualify" and data.get("action_data"):
                qual_res = await client.post(
                    f"{AI_CORE_URL}/qualify",
                    json=data["action_data"],
                )
                if qual_res.status_code == 200:
                    result = qual_res.json()
                    result_text = format_qualification_result(result)
                    await send_message(chat_id, result_text)
                    await send_message(
                        chat_id,
                        "Хотите записаться на бесплатную консультацию с юристом?",
                        reply_markup={
                            "inline_keyboard": [
                                [{"text": "✅ Да, записаться", "callback_data": "schedule_consultation"}],
                                [{"text": "❓ У меня ещё вопросы", "callback_data": "start_qualification"}],
                            ]
                        },
                    )
                    session.state = "idle"
                    sessions[chat_id] = session

    except Exception as e:
        logger.error(f"AI Core error: {e}")
        await send_message(
            chat_id, "Извините, произошла техническая ошибка. Попробуйте ещё раз или позвоните нам: 8 800 123-45-67"
        )


def format_qualification_result(result: dict) -> str:
    """Format qualification result for Telegram."""
    parts = []

    if result.get("is_eligible"):
        parts.append("✅ <b>Вы подходите под процедуру банкротства!</b>\n")
    else:
        parts.append("⚠️ <b>Требуется дополнительная проверка</b>\n")

    proc = result.get("procedure_type", "")
    if proc == "asset_realization":
        parts.append("📋 Рекомендуемая процедура: <b>реализация имущества</b>")
    elif proc == "restructuring":
        parts.append("📋 Рекомендуемая процедура: <b>реструктуризация долгов</b>")

    cost_min = result.get("estimated_cost_min", 0)
    cost_max = result.get("estimated_cost_max", 0)
    if cost_min and cost_max:
        parts.append(f"💰 Стоимость: <b>{cost_min:,.0f}–{cost_max:,.0f} ₽</b>")

    dur_min = result.get("estimated_duration_months_min", 0)
    dur_max = result.get("estimated_duration_months_max", 0)
    if dur_min and dur_max:
        parts.append(f"⏱ Срок: <b>{dur_min}–{dur_max} месяцев</b>")

    risk = result.get("risk_level", "")
    risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(risk, "")
    if risk:
        parts.append(f"{risk_emoji} Уровень риска: <b>{risk}</b>")

    factors = result.get("risk_factors", [])
    if factors:
        parts.append(f"\n⚠️ Факторы риска: {', '.join(factors)}")

    return "\n".join(parts)


async def handle_consultant(chat_id: int, text: str):
    """Handle FAQ-bot consultant messages."""
    session = sessions.get(chat_id, Session(chat_id=chat_id))

    # Call backend consultant endpoint
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(
                f"{BACKEND_URL}/ai/consultant",
                json={
                    "message": text,
                    "conversation_id": session.session_id,
                    "channel": "telegram",
                    "metadata": {"telegram_chat_id": chat_id},
                },
            )
            data = res.json()

            # Update session with new conversation_id if provided
            if data.get("conversation_id"):
                session.session_id = data["conversation_id"]
                sessions[chat_id] = session

            # Send reply
            reply = data["reply"]
            await send_message(chat_id, reply)

            # If CTA present, add inline button
            if data.get("cta"):
                cta = data["cta"]
                button_text = cta.get("button_text", "Оценить мою ситуацию бесплатно")
                await send_message(
                    chat_id,
                    cta.get("text", ""),
                    reply_markup={"inline_keyboard": [[{"text": button_text, "callback_data": "start_qualification"}]]},
                )
    except Exception as e:
        logger.error(f"Consultant error: {e}")
        await send_message(
            chat_id,
            "Извините, произошла ошибка. Попробуйте позже или перейдите к квалификации.",
            reply_markup={
                "inline_keyboard": [[{"text": "Начать квалификацию", "callback_data": "start_qualification"}]]
            },
        )


async def handle_message(chat_id: int, text: str):
    """Route incoming message based on session state."""
    session = sessions.get(chat_id)

    if not session or text == "/start":
        await handle_start(chat_id)
        return

    if session.state == "qualifying":
        await process_qualification(chat_id, text)
    elif session.state == "client":
        # TODO: look up case by number or phone
        await send_message(chat_id, "Функция проверки статуса дела будет доступна в ближайшее время.")
    elif session.state == "idle":
        # New: FAQ-bot consultant mode
        await handle_consultant(chat_id, text)
    else:
        await handle_start(chat_id)


async def poll_updates():
    """Long-polling loop for Telegram updates."""
    offset = 0
    logger.info("Telegram bot started polling...")

    async with httpx.AsyncClient(timeout=60.0) as client:
        while True:
            try:
                res = await client.get(
                    f"{TELEGRAM_API}/getUpdates",
                    params={"offset": offset, "timeout": 30},
                )
                updates = res.json().get("result", [])

                for update in updates:
                    offset = update["update_id"] + 1

                    if "message" in update and "text" in update["message"]:
                        chat_id = update["message"]["chat"]["id"]
                        text = update["message"]["text"]
                        await handle_message(chat_id, text)

                    elif "callback_query" in update:
                        cb = update["callback_query"]
                        chat_id = cb["message"]["chat"]["id"]
                        await handle_callback(chat_id, cb["data"])
                        # Answer callback to remove loading indicator
                        await client.post(
                            f"{TELEGRAM_API}/answerCallbackQuery",
                            json={"callback_query_id": cb["id"]},
                        )

            except httpx.TimeoutException:
                continue
            except Exception as e:
                logger.error(f"Polling error: {e}")
                await asyncio.sleep(5)


if __name__ == "__main__":
    if not BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not set")
        exit(1)
    asyncio.run(poll_updates())
