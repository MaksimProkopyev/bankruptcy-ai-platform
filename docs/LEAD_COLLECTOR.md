# Lead Collector (Gov Sources)

## Что реализовано

- Таблица `leads` + миграция `004_lead_collector`.
- Сервисный пайплайн: `fetch -> filter -> dedup -> save`.
- Источники: `fssp`, `kad_arbitr`, `efrsb`, `fns`, `rosreestr`.
- API:
  - `GET /api/v1/lead-sources/stats`
  - `GET /api/v1/lead-sources/{source}/leads`
  - `POST /api/v1/lead-sources/{source}/run`
  - `POST /api/v1/lead-sources/leads/{lead_id}/convert`
- Воркеры:
  - `python -m workers.lead_collectors`
  - `python -m workers.outreach`

## Быстрый запуск (локально)

1. Применить миграции:
```bash
cd backend
alembic upgrade head
```

2. Запустить один сбор:
```bash
python3 -m workers.lead_collectors --once --source fssp
```

3. Запустить один цикл outreach:
```bash
python3 -m workers.outreach --once
```

4. Ручной запуск из API:
```bash
POST /api/v1/lead-sources/fssp/run
```

## Важные env

- `LEAD_COLLECTOR_MOCK_MODE=true` для разработки без внешних API.
- Для прод-интеграций нужны:
  - `FSSP_API_URL`, `FSSP_API_KEY`
  - `KAD_API_URL`, `KAD_API_KEY`
  - `EFRSB_API_URL`, `EFRSB_API_KEY`
  - `FNS_API_URL`
  - `ROSREESTR_API_URL`, `ROSREESTR_API_KEY`
- Для outreach в real-mode:
  - `LEAD_OUTREACH_SMS_API_URL`, `LEAD_OUTREACH_SMS_API_KEY`
  - `LEAD_OUTREACH_EMAIL_API_URL`, `LEAD_OUTREACH_EMAIL_API_KEY`
  - `LEAD_OUTREACH_TELEGRAM_BOT_TOKEN`
