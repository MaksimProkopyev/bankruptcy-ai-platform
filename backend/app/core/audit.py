"""
Утилита для записи в audit_log.
Вызывается из роутеров после мутирующих операций.
"""

import json
import uuid
from typing import Any, Dict, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def log_action(
    db: AsyncSession,
    *,
    user_id: Optional[uuid.UUID],
    action: str,  # "create", "update", "delete", "login", "logout"
    entity_type: str,  # "case", "user", "document", "payment", ...
    entity_id: Optional[uuid.UUID] = None,
    changes: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    """
    Вставляет запись в audit_log.
    Использование:
        await log_action(db, user_id=current_user.id, action="update",
                         entity_type="case", entity_id=case_id,
                         changes={"status": {"old": "new", "new": "active"}},
                         ip_address=request.client.host,
                         user_agent=request.headers.get("user-agent"))
    """
    await db.execute(
        text("""
            INSERT INTO audit_log (id, user_id, action, entity_type, entity_id,
                                   changes, ip_address, user_agent)
            VALUES (:id, :user_id, :action, :entity_type, :entity_id,
                    :changes::jsonb, :ip_address::inet, :user_agent)
        """),
        {
            "id": uuid.uuid4(),
            "user_id": user_id,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "changes": json.dumps(changes) if changes else None,
            "ip_address": ip_address,
            "user_agent": user_agent,
        },
    )
    # Не делаем commit здесь — caller управляет транзакцией
