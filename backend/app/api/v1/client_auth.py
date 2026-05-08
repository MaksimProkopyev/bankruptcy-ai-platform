"""Client auth — phone-based authentication for personal cabinet.

Flow: phone → SMS code → verify → JWT token (client scope)
"""

import random
import string
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jose import jwt

from app.db.session import get_db
from app.models.models import Client
from app.core.config import settings

router = APIRouter()

# In-memory code store (use Redis in production)
_pending_codes: dict[str, dict] = {}


class PhoneRequest(BaseModel):
    phone: str


class VerifyRequest(BaseModel):
    phone: str
    code: str


class ClientTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    client_id: str
    client_name: str


def _generate_code() -> str:
    return "".join(random.choices(string.digits, k=6))


def _create_client_token(client_id: UUID, phone: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=24)
    payload = {
        "sub": str(client_id),
        "phone": phone,
        "scope": "client",
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


@router.post("/send-code")
async def send_code(data: PhoneRequest, db: AsyncSession = Depends(get_db)):
    """Send SMS verification code to client's phone.
    
    Checks that the phone exists in the system (registered client).
    """
    phone = data.phone.strip()

    # Check client exists
    result = await db.execute(select(Client).where(Client.phone == phone))
    client = result.scalar_one_or_none()

    if not client:
        # Don't reveal whether the phone exists
        # but still return success to prevent enumeration
        return {"message": "Код отправлен", "expires_in": 300}

    code = _generate_code()
    _pending_codes[phone] = {
        "code": code,
        "client_id": str(client.id),
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5),
        "attempts": 0,
    }

    # TODO: Send SMS via SMS gateway (SMS.ru, SMSC, etc.)
    # For dev, log the code
    print(f"[DEV] SMS code for {phone}: {code}")

    return {"message": "Код отправлен", "expires_in": 300}


@router.post("/verify-code", response_model=ClientTokenResponse)
async def verify_code(data: VerifyRequest, db: AsyncSession = Depends(get_db)):
    """Verify SMS code and return client JWT token."""
    phone = data.phone.strip()
    pending = _pending_codes.get(phone)

    if not pending:
        raise HTTPException(status_code=400, detail="Код не найден. Запросите новый.")

    # Check expiration
    if datetime.now(timezone.utc) > pending["expires_at"]:
        del _pending_codes[phone]
        raise HTTPException(status_code=400, detail="Код истёк. Запросите новый.")

    # Check attempts
    pending["attempts"] += 1
    if pending["attempts"] > 5:
        del _pending_codes[phone]
        raise HTTPException(status_code=429, detail="Слишком много попыток. Запросите новый код.")

    # Verify code
    if data.code != pending["code"]:
        raise HTTPException(status_code=400, detail="Неверный код")

    client_id = UUID(pending["client_id"])
    del _pending_codes[phone]

    # Get client
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    token = _create_client_token(client.id, phone)

    return ClientTokenResponse(
        access_token=token,
        client_id=str(client.id),
        client_name=f"{client.first_name} {client.last_name}",
    )
