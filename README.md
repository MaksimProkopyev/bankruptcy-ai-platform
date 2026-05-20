# Bankruptcy AI Platform

Внутренняя платформа управления делами о банкротстве физических лиц: CRM для сотрудников, личный кабинет клиента, лидогенерация и фоновая обработка документов.

---

## Сервисы

| Сервис | Порт | Назначение |
|---|---|---|
| `backend` | 8000 | Основной API (FastAPI) |
| `ai-core` | 8001 | Обработка документов, OCR, RAG, LLM-вызовы |
| `leadgen` | 8002 | Сервис лидогенерации (FastAPI) |
| `site-frontend` | 3000 | Публичный сайт (Next.js) |
| `staff-frontend` | 3001 | Портал сотрудника (Next.js) |
| `crm-frontend` | 3002 | CRM для персонала (Next.js) |
| `lk-frontend` | 3003 | Личный кабинет клиента (Next.js) |
| `leadgen-frontend` | 3004 | Фронт лидогенерации (Next.js) |
| `postgres` | 5432 | PostgreSQL 16 + pgvector |
| `redis` | 6379 | Кэш и очередь задач |
| `minio` | 9000 / 9001 | S3-совместимое хранилище файлов / веб-консоль |
| `worker` | — | Фоновый воркер (OCR, генерация документов) |
| `lead-collector-worker` | — | Сборщик лидов из госреестров (ФССП, КАД, ЕФРСБ, ФНС, Росреестр) |
| `lead-outreach-worker` | — | Воркер рассылок (SMS, email, Telegram) |
| `ollama` | 11434 | Локальная LLM (опционально, профиль `ollama`) |
| `telegram-bot` | — | Telegram-бот (опционально, профиль `telegram`) |

---

## Структура монорепо

```
.
├── backend/            # Основной FastAPI-бэкенд, Alembic-миграции, фоновые воркеры
│   ├── app/
│   │   ├── api/v1/     # Роутеры: auth, clients, cases, documents, billing, staff, cabinet и др.
│   │   ├── core/       # Конфиг, безопасность, разрешения (RBAC + RLS)
│   │   ├── db/         # SQLAlchemy, начальная схема БД
│   │   ├── models/     # ORM-модели
│   │   ├── schemas/    # Pydantic-схемы
│   │   └── services/   # Бизнес-логика, StorageService, воркер
│   └── workers/        # lead_collectors.py, outreach.py
│
├── leadgen/            # Сервис лидогенерации (FastAPI, порт 8002)
│   ├── routers/        # leads, prospects, ai, stats, webhooks
│   └── adapters/       # WhatsApp (Green API), VK, Meta
│
├── ai-core/            # Сервис обработки: OCR, RAG, LLM, агенты
│   ├── agents/
│   ├── llm/
│   ├── ocr/
│   └── rag/
│
├── crm-frontend/       # CRM-интерфейс для сотрудников (Next.js 14)
├── lk-frontend/        # Личный кабинет клиента (Next.js 14)
├── leadgen-frontend/   # Фронт для лидов и проспектов (Next.js 14)
├── staff-frontend/     # Портал сотрудника: задачи, дашборд (Next.js 14)
├── site-frontend/      # Публичный сайт (Next.js 14)
│
├── mobile/             # Мобильное приложение (React Native / Expo)
├── packages/           # Общие пакеты (ui-компоненты)
│
├── infra/
│   └── nginx/          # Конфиги vhost: api, crm, lk, staff, leadgen, site
│
├── scripts/            # setup.sh, update_admin.sql
├── docs/               # ADR, API-контракты, планы спринтов
├── tests/              # E2E и smoke-тесты
│
├── docker-compose.yml
├── .env.example
└── pnpm-workspace.yaml
```

---

## Быстрый старт

```bash
git clone <repo-url> bankruptcy-ai-platform
cd bankruptcy-ai-platform

cp .env.example .env
# Отредактируй .env: заполни POSTGRES_PASSWORD, JWT_SECRET, INTERNAL_SECRET и ключи внешних сервисов

docker compose up -d
```

Для запуска с локальной LLM:

```bash
docker compose --profile ollama up -d
```

Для запуска Telegram-бота:

```bash
docker compose --profile telegram up -d
```

---

## Домены

| Домен | Сервис | Порт |
|---|---|---|
| `nssb-maximum.ru` | site-frontend | 3000 |
| `api.nssb-maximum.ru` | backend | 8000 |
| `crm.nssb-maximum.ru` | crm-frontend | 3002 |
| `lk.nssb-maximum.ru` | lk-frontend | 3003 |
| `staff.nssb-maximum.ru` | staff-frontend | 3001 |
| `leadgen.nssb-maximum.ru` | leadgen | 8002 |

Nginx-конфиги: `infra/nginx/*.conf`. SSL — Let's Encrypt (`/etc/letsencrypt/live/nssb-maximum.ru/`).

Эндпоинт `/api/v1/internal/` закрыт на уровне nginx: доступен только с localhost и из подсетей Docker.

---

## Группы API

### backend (`/api/v1`)

| Префикс | Описание |
|---|---|
| `/auth` | Аутентификация сотрудников (JWT) |
| `/client-auth` | Аутентификация клиентов (SMS OTP) |
| `/users` | Управление пользователями-сотрудниками |
| `/clients` | Профили клиентов |
| `/cases` | Дела о банкротстве |
| `/documents` | Документы по делам |
| `/billing` | Платежи и счета |
| `/notifications` | Уведомления |
| `/analytics` | Аналитика и отчёты |
| `/lead-sources` | Источники лидов |
| `/prospects` | Проспекты (предварительные лиды) |
| `/staff` | Личный кабинет сотрудника (задачи, дашборд, предложения) |
| `/cabinet` | Личный кабинет клиента |
| `/anticollector` | Сервис антиколлектор (публичная регистрация) |
| `/library` | Библиотека документов (Yandex Object Storage) |
| `/storage` | Объектное хранилище (legacy) |
| `/internal` | Внутренние эндпоинты (secret-аутентификация, без JWT) |

### leadgen (`/api/v1`)

| Префикс | Описание |
|---|---|
| `/leads` | Управление лидами |
| `/prospects` | Проспекты лидогенерации |
| `/ai` | AI-консультант (предварительная квалификация) |
| `/stats` | Статистика лидогенерации |
| `/webhooks` | Вебхуки WhatsApp, VK, Meta |

---

## Переменные окружения

| Переменная | Описание |
|---|---|
| `JWT_SECRET` / `SECRET_KEY` | Секрет для подписи JWT-токенов |
| `INTERNAL_SECRET` | Секрет для межсервисных internal-запросов |
| `DATABASE_URL` | PostgreSQL DSN (`postgresql+asyncpg://...`) |
| `REDIS_URL` | Redis DSN (`redis://:password@host:6379/0`) |
| `POSTGRES_PASSWORD` | Пароль пользователя `postgres` |
| `REDIS_PASSWORD` | Пароль Redis |
| `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` | Учётные данные MinIO |
| `S3_ENDPOINT` / `S3_ACCESS_KEY` / `S3_SECRET_KEY` / `S3_BUCKET` | MinIO/S3 для документов клиентов |
| `YC_ACCESS_KEY` / `YC_SECRET_KEY` / `YC_BUCKET_NAME` | Yandex Object Storage для базы знаний |
| `ANTHROPIC_API_KEY` | Ключ Anthropic API |
| `OPENAI_API_KEY` | Ключ OpenAI API |
| `GIGACHAT_API_KEY` | Ключ GigaChat API |
| `YANDEX_API_KEY` / `YANDEX_FOLDER_ID` | Yandex Cloud ML |
| `OLLAMA_BASE_URL` | URL Ollama (по умолчанию `http://ollama:11434/v1`) |
| `TELEGRAM_BOT_TOKEN` | Токен Telegram-бота |
| `GREEN_API_TOKEN` | Токен Green API (WhatsApp) |
| `VK_API_TOKEN` | Токен VK API |
| `TOCHKA_API_TOKEN` / `TOCHKA_ACCOUNT_ID` | Банк Точка (платежи) |
| `SMS_API_KEY` / `SMS_PROVIDER` | SMS-шлюз для OTP-аутентификации клиентов |
| `FSSP_API_KEY` / `KAD_API_KEY` / `EFRSB_API_KEY` | Ключи госреестров для сборщика лидов |
| `LEAD_COLLECTOR_MOCK_MODE` | `true` — не ходить в реальные API реестров |
| `LEAD_OUTREACH_DRY_RUN` | `true` — не отправлять реальные сообщения |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Время жизни JWT (по умолчанию 1440 мин) |

---

## Команды

### Миграции БД

```bash
# Применить все миграции (Alembic)
docker compose exec backend alembic upgrade head

# Создать новую миграцию
docker compose exec backend alembic revision --autogenerate -m "описание"

# Откатить одну миграцию
docker compose exec backend alembic downgrade -1
```

### Логи

```bash
# Все сервисы
docker compose logs -f

# Конкретный сервис
docker compose logs -f backend
docker compose logs -f leadgen
docker compose logs -f worker
```

### Управление сервисами

```bash
# Перезапустить один сервис
docker compose restart backend

# Пересобрать и перезапустить после изменений кода
docker compose up -d --build backend

# Остановить всё
docker compose down

# Остановить и удалить тома (полный сброс БД и файлов)
docker compose down -v
```

### Разработка без Docker

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (pnpm workspaces)
pnpm install
pnpm --filter crm-frontend dev
pnpm --filter lk-frontend dev
```
