# Cursor Prompt: RBAC + RLS + Audit Log

## Контекст

Проект: `bankruptcy-ai-platform` (монорепо)
Сервис: `backend/` — FastAPI (Python 3.12), SQLAlchemy 2.0 async, PostgreSQL 16
VM: `89.169.169.103`, код в `/opt/bankruptcy-ai`

### Роли (PostgreSQL enum `user_role`)
```
admin, operations_director, lawyer, paralegal,
client_manager, marketer, ai_engineer, client
```

### Таблицы БД (реальные, проверено `\dt public.*`)
```
ai_tasks, audit_log, case_events, cases, clients,
creditors, deadlines, document_checklist, documents,
knowledge_base, messages, notifications, payments, users
```

### `users` — ключевые колонки
```sql
id uuid PK, email varchar, password_hash varchar,
role user_role NOT NULL, is_active boolean
```

### `audit_log` — существующая таблица
```sql
id uuid PK, user_id uuid FK users,
action varchar(100), entity_type varchar(50),
entity_id uuid, changes jsonb,
ip_address inet, user_agent text, created_at timestamptz
```

### `cases` — связи с users (из FK в users)
```sql
assigned_lawyer_id uuid FK users
assigned_manager_id uuid FK users
assigned_paralegal_id uuid FK users
-- client_id связан через clients
```

---

## Задача

Реализовать полный RBAC стек: матрица прав → FastAPI dependency → RLS в PostgreSQL → audit log helper.

---

## Файл 1: `backend/app/core/permissions.py`

Создать файл с нуля.

```python
"""
RBAC permission matrix и FastAPI dependencies.
Используется во всех роутерах через Depends().
"""
from enum import Enum
from typing import Set, Dict
from fastapi import Depends, HTTPException, status
from app.core.auth import get_current_user  # существующий dep
from app.models.user import User  # существующая модель


class UserRole(str, Enum):
    ADMIN = "admin"
    OPERATIONS_DIRECTOR = "operations_director"
    LAWYER = "lawyer"
    PARALEGAL = "paralegal"
    CLIENT_MANAGER = "client_manager"
    MARKETER = "marketer"
    AI_ENGINEER = "ai_engineer"
    CLIENT = "client"


# Матрица прав: resource -> action -> set of allowed roles
# resource = группа эндпоинтов (совпадает с префиксом роутера)
PERMISSIONS: Dict[str, Dict[str, Set[UserRole]]] = {
    "users": {
        "read":   {UserRole.ADMIN, UserRole.OPERATIONS_DIRECTOR},
        "write":  {UserRole.ADMIN},
        "delete": {UserRole.ADMIN},
    },
    "cases": {
        "read":   {UserRole.ADMIN, UserRole.OPERATIONS_DIRECTOR, UserRole.LAWYER,
                   UserRole.PARALEGAL, UserRole.CLIENT_MANAGER, UserRole.CLIENT},
        "write":  {UserRole.ADMIN, UserRole.OPERATIONS_DIRECTOR, UserRole.LAWYER,
                   UserRole.CLIENT_MANAGER},
        "delete": {UserRole.ADMIN, UserRole.OPERATIONS_DIRECTOR},
    },
    "clients": {
        "read":   {UserRole.ADMIN, UserRole.OPERATIONS_DIRECTOR, UserRole.LAWYER,
                   UserRole.PARALEGAL, UserRole.CLIENT_MANAGER, UserRole.MARKETER},
        "write":  {UserRole.ADMIN, UserRole.OPERATIONS_DIRECTOR, UserRole.LAWYER,
                   UserRole.CLIENT_MANAGER},
        "delete": {UserRole.ADMIN, UserRole.OPERATIONS_DIRECTOR},
    },
    "documents": {
        "read":   {UserRole.ADMIN, UserRole.OPERATIONS_DIRECTOR, UserRole.LAWYER,
                   UserRole.PARALEGAL, UserRole.CLIENT_MANAGER, UserRole.CLIENT},
        "write":  {UserRole.ADMIN, UserRole.OPERATIONS_DIRECTOR, UserRole.LAWYER,
                   UserRole.PARALEGAL, UserRole.CLIENT_MANAGER},
        "delete": {UserRole.ADMIN, UserRole.OPERATIONS_DIRECTOR, UserRole.LAWYER},
    },
    "payments": {
        "read":   {UserRole.ADMIN, UserRole.OPERATIONS_DIRECTOR, UserRole.LAWYER,
                   UserRole.CLIENT_MANAGER, UserRole.CLIENT},
        "write":  {UserRole.ADMIN, UserRole.OPERATIONS_DIRECTOR, UserRole.CLIENT_MANAGER},
        "delete": {UserRole.ADMIN},
    },
    "leads": {
        "read":   {UserRole.ADMIN, UserRole.OPERATIONS_DIRECTOR, UserRole.CLIENT_MANAGER,
                   UserRole.MARKETER},
        "write":  {UserRole.ADMIN, UserRole.OPERATIONS_DIRECTOR, UserRole.CLIENT_MANAGER},
        "delete": {UserRole.ADMIN, UserRole.OPERATIONS_DIRECTOR},
    },
    "tasks": {
        "read":   {UserRole.ADMIN, UserRole.OPERATIONS_DIRECTOR, UserRole.LAWYER,
                   UserRole.PARALEGAL, UserRole.CLIENT_MANAGER},
        "write":  {UserRole.ADMIN, UserRole.OPERATIONS_DIRECTOR, UserRole.LAWYER,
                   UserRole.PARALEGAL, UserRole.CLIENT_MANAGER},
        "delete": {UserRole.ADMIN, UserRole.OPERATIONS_DIRECTOR},
    },
    "deadlines": {
        "read":   {UserRole.ADMIN, UserRole.OPERATIONS_DIRECTOR, UserRole.LAWYER,
                   UserRole.PARALEGAL, UserRole.CLIENT_MANAGER, UserRole.CLIENT},
        "write":  {UserRole.ADMIN, UserRole.OPERATIONS_DIRECTOR, UserRole.LAWYER,
                   UserRole.PARALEGAL},
        "delete": {UserRole.ADMIN, UserRole.OPERATIONS_DIRECTOR, UserRole.LAWYER},
    },
    "knowledge": {
        "read":   {UserRole.ADMIN, UserRole.OPERATIONS_DIRECTOR, UserRole.LAWYER,
                   UserRole.PARALEGAL, UserRole.AI_ENGINEER},
        "write":  {UserRole.ADMIN, UserRole.AI_ENGINEER},
        "delete": {UserRole.ADMIN},
    },
    "analytics": {
        "read":   {UserRole.ADMIN, UserRole.OPERATIONS_DIRECTOR, UserRole.MARKETER},
        "write":  {UserRole.ADMIN},
        "delete": {UserRole.ADMIN},
    },
    "admin": {
        "read":   {UserRole.ADMIN},
        "write":  {UserRole.ADMIN},
        "delete": {UserRole.ADMIN},
    },
    "messages": {
        "read":   {UserRole.ADMIN, UserRole.OPERATIONS_DIRECTOR, UserRole.LAWYER,
                   UserRole.PARALEGAL, UserRole.CLIENT_MANAGER, UserRole.CLIENT},
        "write":  {UserRole.ADMIN, UserRole.OPERATIONS_DIRECTOR, UserRole.LAWYER,
                   UserRole.PARALEGAL, UserRole.CLIENT_MANAGER, UserRole.CLIENT},
        "delete": {UserRole.ADMIN, UserRole.OPERATIONS_DIRECTOR},
    },
    "ai_tasks": {
        "read":   {UserRole.ADMIN, UserRole.AI_ENGINEER, UserRole.OPERATIONS_DIRECTOR},
        "write":  {UserRole.ADMIN, UserRole.AI_ENGINEER},
        "delete": {UserRole.ADMIN},
    },
}


def require_roles(*roles: UserRole):
    """
    FastAPI dependency. Пример использования:
        @router.get("/", dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.LAWYER))])
    или:
        current_user: User = Depends(require_roles(UserRole.ADMIN))
    """
    async def _check(current_user: User = Depends(get_current_user)) -> User:
        if not current_user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Account inactive")
        if current_user.role not in {r.value for r in roles}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' is not allowed. "
                       f"Required: {[r.value for r in roles]}"
            )
        return current_user
    return _check


def require_permission(resource: str, action: str):
    """
    Dependency по матрице прав. Пример:
        @router.delete("/{id}", dependencies=[Depends(require_permission("cases", "delete"))])
    """
    async def _check(current_user: User = Depends(get_current_user)) -> User:
        if not current_user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Account inactive")
        allowed = PERMISSIONS.get(resource, {}).get(action, set())
        if UserRole(current_user.role) not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {resource}:{action}"
            )
        return current_user
    return _check


# Shorthand helpers (наиболее частые паттерны)
require_admin = require_roles(UserRole.ADMIN)
require_admin_or_ops = require_roles(UserRole.ADMIN, UserRole.OPERATIONS_DIRECTOR)
require_staff = require_roles(
    UserRole.ADMIN, UserRole.OPERATIONS_DIRECTOR, UserRole.LAWYER,
    UserRole.PARALEGAL, UserRole.CLIENT_MANAGER
)
```

---

## Файл 2: `backend/app/core/audit.py`

Создать файл с нуля.

```python
"""
Утилита для записи в audit_log.
Вызывается из роутеров после мутирующих операций.
"""
import uuid
from typing import Optional, Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


async def log_action(
    db: AsyncSession,
    *,
    user_id: Optional[uuid.UUID],
    action: str,                     # "create", "update", "delete", "login", "logout"
    entity_type: str,                # "case", "user", "document", "payment", ...
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
            "changes": __import__("json").dumps(changes) if changes else None,
            "ip_address": ip_address,
            "user_agent": user_agent,
        }
    )
    # Не делаем commit здесь — caller управляет транзакцией
```

---

## Файл 3a: `backend/alembic/versions/009_clients_user_id.py`

Добавить `user_id` в таблицу `clients`. Это обязательный prerequisite для RLS роли `client`.

**Важно:** найди последнюю миграцию в `backend/alembic/versions/` и подставь её `revision` как `down_revision`.

```python
"""Add user_id to clients table

Revision ID: 009_clients_user_id
Revises: <LAST_REVISION>
Create Date: 2026-05-09
"""
from alembic import op
import sqlalchemy as sa

revision = '009_clients_user_id'
down_revision = '<LAST_REVISION>'  # ← подставить
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('clients',
        sa.Column('user_id', sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'),
                  nullable=True)
    )
    op.create_index('idx_clients_user_id', 'clients', ['user_id'])


def downgrade() -> None:
    op.drop_index('idx_clients_user_id', table_name='clients')
    op.drop_column('clients', 'user_id')
```

После применения этой миграции: при создании клиентского аккаунта в `users` (role='client') — устанавливать `clients.user_id = users.id`. Найди место в коде где создаётся клиент (роутер `clients.py` или `auth.py`) и добавь эту связку.

---

## Файл 3b: `backend/alembic/versions/010_rbac_rls.py`

Создать новый файл Alembic-миграции.

**Важно:** найди последнюю миграцию в `backend/alembic/versions/` и подставь её `revision` как `down_revision` в новом файле.

```python
"""RBAC: RLS policies on core tables

Revision ID: 010_rbac_rls
Revises: 009_clients_user_id
Create Date: 2026-05-09
"""
from alembic import op
import sqlalchemy as sa

revision = '010_rbac_rls'
down_revision = '009_clients_user_id'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Создать роль приложения если не существует
    # FastAPI устанавливает session vars, RLS читает их
    conn.execute(sa.text("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_user') THEN
                CREATE ROLE app_user;
            END IF;
        END
        $$;
    """))

    # 2. Включить RLS на ключевых таблицах
    for table in ["cases", "documents", "payments", "messages",
                  "notifications", "deadlines", "case_events",
                  "document_checklist", "creditors"]:
        conn.execute(sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;"))
        conn.execute(sa.text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;"))

    # 3. Политики для таблицы cases
    # admin и operations_director видят всё
    conn.execute(sa.text("""
        CREATE POLICY cases_admin_all ON cases
            USING (
                current_setting('app.current_user_role', true) IN ('admin', 'operations_director')
            );
    """))
    # lawyer видит свои дела (assigned_lawyer_id)
    conn.execute(sa.text("""
        CREATE POLICY cases_lawyer_own ON cases
            USING (
                current_setting('app.current_user_role', true) = 'lawyer'
                AND assigned_lawyer_id = current_setting('app.current_user_id', true)::uuid
            );
    """))
    # paralegal видит дела куда назначен
    conn.execute(sa.text("""
        CREATE POLICY cases_paralegal_own ON cases
            USING (
                current_setting('app.current_user_role', true) = 'paralegal'
                AND assigned_paralegal_id = current_setting('app.current_user_id', true)::uuid
            );
    """))
    # client_manager видит свои дела (assigned_manager_id)
    conn.execute(sa.text("""
        CREATE POLICY cases_manager_own ON cases
            USING (
                current_setting('app.current_user_role', true) = 'client_manager'
                AND assigned_manager_id = current_setting('app.current_user_id', true)::uuid
            );
    """))
    # client видит только своё дело (через clients.user_id — добавлено в 009)
    conn.execute(sa.text("""
        CREATE POLICY cases_client_own ON cases
            USING (
                current_setting('app.current_user_role', true) = 'client'
                AND client_id IN (
                    SELECT id FROM clients
                    WHERE user_id = current_setting('app.current_user_id', true)::uuid
                )
            );
    """))

    # 4. Политики documents (наследуют доступ к делу)
    conn.execute(sa.text("""
        CREATE POLICY documents_by_case ON documents
            USING (
                current_setting('app.current_user_role', true) IN ('admin', 'operations_director')
                OR case_id IN (
                    SELECT id FROM cases
                )
            );
    """))
    # Примечание: documents RLS полагается на то, что cases уже фильтрованы.
    # Для полной изоляции subquery в documents_by_case должна учитывать роль.
    # Реализация ниже — полная версия:
    conn.execute(sa.text("DROP POLICY IF EXISTS documents_by_case ON documents;"))
    conn.execute(sa.text("""
        CREATE POLICY documents_by_case ON documents
            USING (
                current_setting('app.current_user_role', true) IN ('admin', 'operations_director')
                OR (
                    current_setting('app.current_user_role', true) = 'lawyer'
                    AND case_id IN (
                        SELECT id FROM cases
                        WHERE assigned_lawyer_id = current_setting('app.current_user_id', true)::uuid
                    )
                )
                OR (
                    current_setting('app.current_user_role', true) = 'paralegal'
                    AND case_id IN (
                        SELECT id FROM cases
                        WHERE assigned_paralegal_id = current_setting('app.current_user_id', true)::uuid
                    )
                )
                OR (
                    current_setting('app.current_user_role', true) = 'client_manager'
                    AND case_id IN (
                        SELECT id FROM cases
                        WHERE assigned_manager_id = current_setting('app.current_user_id', true)::uuid
                    )
                )
                OR (
                    current_setting('app.current_user_role', true) = 'client'
                    AND case_id IN (
                        SELECT c.id FROM cases c
                        JOIN clients cl ON cl.case_id = c.id
                        WHERE cl.user_id = current_setting('app.current_user_id', true)::uuid
                    )
                )
            );
    """))

    # 5. notifications — client_id FK to clients (не user_id!)
    conn.execute(sa.text("""
        CREATE POLICY notifications_own ON notifications
            USING (
                current_setting('app.current_user_role', true) IN ('admin', 'operations_director')
                OR (
                    current_setting('app.current_user_role', true) != 'client'
                    AND user_id = current_setting('app.current_user_id', true)::uuid
                )
                OR (
                    current_setting('app.current_user_role', true) = 'client'
                    AND client_id IN (
                        SELECT id FROM clients
                        WHERE user_id = current_setting('app.current_user_id', true)::uuid
                    )
                )
            );
    """))

    # 6. payments — аналогично documents (через case_id)
    conn.execute(sa.text("""
        CREATE POLICY payments_by_case ON payments
            USING (
                current_setting('app.current_user_role', true) IN ('admin', 'operations_director', 'client_manager')
                OR (
                    current_setting('app.current_user_role', true) = 'lawyer'
                    AND case_id IN (
                        SELECT id FROM cases
                        WHERE assigned_lawyer_id = current_setting('app.current_user_id', true)::uuid
                    )
                )
                OR (
                    current_setting('app.current_user_role', true) = 'client'
                    AND case_id IN (
                        SELECT id FROM cases
                        WHERE client_id IN (
                            SELECT id FROM clients
                            WHERE user_id = current_setting('app.current_user_id', true)::uuid
                        )
                    )
                )
            );
    """))

    # 7. messages — staff видит по делу, client видит своё дело
    conn.execute(sa.text("""
        CREATE POLICY messages_by_case ON messages
            USING (
                current_setting('app.current_user_role', true) IN ('admin', 'operations_director')
                OR sent_by = current_setting('app.current_user_id', true)::uuid
                OR (
                    current_setting('app.current_user_role', true) IN ('lawyer', 'paralegal', 'client_manager')
                    AND case_id IN (
                        SELECT id FROM cases
                        WHERE assigned_lawyer_id = current_setting('app.current_user_id', true)::uuid
                           OR assigned_paralegal_id = current_setting('app.current_user_id', true)::uuid
                           OR assigned_manager_id = current_setting('app.current_user_id', true)::uuid
                    )
                )
                OR (
                    current_setting('app.current_user_role', true) = 'client'
                    AND client_id IN (
                        SELECT id FROM clients
                        WHERE user_id = current_setting('app.current_user_id', true)::uuid
                    )
                )
            );
    """))

    # 8. deadlines, case_events, document_checklist, creditors — по аналогии с documents
    for table in ["deadlines", "case_events", "document_checklist", "creditors"]:
        conn.execute(sa.text(f"""
            CREATE POLICY {table}_by_case ON {table}
                USING (
                    current_setting('app.current_user_role', true) IN ('admin', 'operations_director')
                    OR (
                        current_setting('app.current_user_role', true) IN ('lawyer', 'paralegal', 'client_manager')
                        AND case_id IN (
                            SELECT id FROM cases
                            WHERE assigned_lawyer_id = current_setting('app.current_user_id', true)::uuid
                               OR assigned_paralegal_id = current_setting('app.current_user_id', true)::uuid
                               OR assigned_manager_id = current_setting('app.current_user_id', true)::uuid
                        )
                    )
                    OR (
                        current_setting('app.current_user_role', true) = 'client'
                        AND case_id IN (
                            SELECT id FROM cases
                            WHERE client_id IN (
                                SELECT id FROM clients
                                WHERE user_id = current_setting('app.current_user_id', true)::uuid
                            )
                        )
                    )
                );
        """))


def downgrade() -> None:
    conn = op.get_bind()

    for table in ["cases", "documents", "payments", "messages",
                  "notifications", "deadlines", "case_events",
                  "document_checklist", "creditors"]:
        # DROP ALL POLICIES
        conn.execute(sa.text(f"""
            DO $$ DECLARE r RECORD;
            BEGIN
                FOR r IN SELECT policyname FROM pg_policies WHERE tablename = '{table}'
                LOOP
                    EXECUTE 'DROP POLICY IF EXISTS ' || r.policyname || ' ON {table}';
                END LOOP;
            END $$;
        """))
        conn.execute(sa.text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;"))
```

---

## Файл 4: обновить `backend/app/core/auth.py` (или `get_current_user`)

Найди функцию `get_current_user` (или аналог — dependency, которая декодирует JWT и возвращает User объект). После получения пользователя из БД добавь установку session variables для RLS:

```python
# После получения user из БД, перед return:
await db.execute(
    text("SELECT set_config('app.current_user_id', :uid, true)"),
    {"uid": str(user.id)}
)
await db.execute(
    text("SELECT set_config('app.current_user_role', :role, true)"),
    {"role": user.role}
)
```

Параметр `true` в `set_config` означает LOCAL (в рамках текущей транзакции) — это правильно для async per-request сессий.

---

## Файл 5: применить dependencies к роутерам

В каждом роутере найди существующий `get_current_user` dependency и замени или дополни через `require_permission`:

```python
# Было (пример):
@router.get("/cases/", ...)
async def list_cases(current_user = Depends(get_current_user)):
    ...

# Стало:
from app.core.permissions import require_permission

@router.get("/cases/", ...)
async def list_cases(current_user = Depends(require_permission("cases", "read"))):
    ...

@router.delete("/cases/{case_id}", ...)
async def delete_case(current_user = Depends(require_permission("cases", "delete"))):
    ...
```

Применить ко всем роутерам в `backend/app/api/v1/`:
- `cases.py` → resource `"cases"`
- `clients.py` → resource `"clients"`
- `documents.py` → resource `"documents"`
- `payments.py` → resource `"payments"`
- `leads.py` → resource `"leads"`
- `tasks.py` → resource `"tasks"`
- `knowledge.py` → resource `"knowledge"`
- `analytics.py` → resource `"analytics"`
- `admin.py` → resource `"admin"`
- `users.py` → resource `"users"`
- `messages.py` → resource `"messages"`

---

## Проверка после реализации

```bash
# Применить миграцию
cd /opt/bankruptcy-ai
sudo docker compose exec backend alembic upgrade head

# Проверить политики
sudo docker compose exec postgres psql -U postgres -d bankruptcy_ai -c \
  "SELECT tablename, policyname, cmd, qual FROM pg_policies ORDER BY tablename;"
```

---

## Важные ограничения

1. **Таблица `clients`**: проверь колонки `user_id` и `case_id`. Если их нет — RBAC на уровне RLS для `client` роли не заработает. Нужно будет добавить колонку или реализовать фильтрацию на уровне Python.

2. **Таблица `messages`**: проверь колонку `case_id`. Если нет — скорректировать политику.

3. **`postgres` superuser обходит RLS** — это нормально. В production connection pool должен использовать отдельную роль `app_user` (не superuser). Для текущего этапа (dev/staging) достаточно Python-уровня RBAC через `require_permission`.

4. **Приоритет**: сначала реализовать файлы 1-2 (permissions.py + audit.py) и файл 4 (set_config в auth). Файл 3 (RLS миграция) — после проверки, что `clients.user_id` и `messages.case_id` существуют.
