# E2E Audit Report — 2026-05-19

**Платформа:** НССБ «Максимум» / Банкротство.AI
**Аудитор:** Claude (автоматический)
**Инструменты:** httpx 0.27, Playwright 1.60, Chromium (headless)

---

## API Smoke

> Base URL: `https://api.nssb-maximum.ru`
> Auth: `POST /api/v1/auth/login` → JWT Bearer
> Примечание: эндпоинты коллекций требуют **trailing slash** (`/cases/`, а не `/cases`), иначе 307 редирект с потерей Authorization-заголовка в httpx.

| Endpoint | Status | Result | Примечание |
|----------|--------|--------|------------|
| GET /health | 200 | ✅ OK | version=0.1.0 |
| POST /api/v1/auth/login | 200 | ✅ OK | token получен |
| GET /api/v1/auth/me | 200 | ✅ OK | role=admin |
| GET /api/v1/cases/ | 200 | ✅ OK | count=0 (БД пустая) |
| GET /api/v1/clients/ | 200 | ✅ OK | count=0 |
| GET /api/v1/prospects/ | 500 | ❌ FAIL | **Internal Server Error** |
| GET /api/v1/analytics/summary | 500 | ❌ FAIL | **Internal Server Error** |
| GET /api/v1/analytics/funnel | 200 | ✅ OK | count=0 |
| GET /api/v1/library/ | 200 | ✅ OK | count=117 документов |
| GET /api/v1/billing/templates | 500 | ❌ FAIL | **Internal Server Error** |
| GET /api/v1/users/ | 200 | ✅ OK | 1 пользователь |
| GET /api/v1/staff/me/tasks | 200 | ✅ OK | count=0 |
| GET /api/v1/staff/me/dashboard | 200 | ✅ OK | данные получены |
| POST /api/v1/client-auth/send-code | 200 | ✅ OK | {"message":"Код отправлен"} |

**API итог: 11 / 14 прошло**

---

## UI Scenarios

### Публичный сайт (nssb-maximum.ru)

| Сценарий | Результат | Подробности |
|----------|-----------|-------------|
| Главная открывается, title корректен | ✅ PASS | title='Банкротство.AI — Списание долгов...' |
| Nav-ссылки не ведут на 404 | ✅ PASS | 8 ссылок проверено, 404 нет |
| Форма / CTA заявки найдена | ❌ FAIL | На главной нет `<form>` с inputs — только JS-кнопки (id=start-chat), которые запускают AI-чат. Лид-форма не обнаружена в DOM. |

> **Скриншот:** `screenshots/01_public_home.png`

### CRM (crm.nssb-maximum.ru)

| Сценарий | Результат | Подробности |
|----------|-----------|-------------|
| Страница логина открывается | ✅ PASS | форма найдена |
| Логин → редирект на /dashboard | ✅ PASS | url=https://crm.nssb-maximum.ru/dashboard |
| Dashboard загружается | ✅ PASS | контент есть, **17 JS-ошибок** (React hydration #418 + analytics/summary CORS/500) |
| Создать клиента [TEST] | ❌ FAIL | Кнопка "Новый клиент" не найдена по селектору; страница `/clients` загружается но кнопка имеет нестандартный текст или находится за auth-редиректом |
| Изменить телефон клиента | ❌ FAIL | client_id не получен (клиент не создан) |
| Создать дело [TEST] | ❌ FAIL | Save-кнопка на форме `/cases/new` не найдена (форма рендерится иначе) |
| Сменить статус дела | ❌ FAIL | case_id не получен (дело не создано) |
| Загрузить PDF в дело | ❌ FAIL | case_id не получен |
| Создать задачу к делу | ❌ FAIL | case_id не получен |
| Раздел /leadgen (Лиды) открывается | ✅ PASS | url=/leadgen, страница загружается |
| Раздел /leadgen/prospects (Проспекты) | ✅ PASS | url=/prospects, страница загружается |
| Навигация /cases | ✅ PASS | 200, не редиректит на /login |
| Навигация /clients | ❌ FAIL | Редиректит на /login (auth cookie теряется при переходе) |
| Навигация /tasks | ❌ FAIL | Маршрут `/tasks` не существует в CRM (нет страницы) |
| Навигация /billing | ✅ PASS | 200 |

> **Скриншоты:** `screenshots/10_crm_login.png`, `11_crm_after_login.png`, `12_crm_dashboard.png`, `13_crm_clients_list.png`, `17_crm_cases_list.png`

### ЛК Клиента (lk.nssb-maximum.ru)

| Сценарий | Результат | Подробности |
|----------|-----------|-------------|
| Страница логина открывается | ❌ FAIL | **503 Service Temporarily Unavailable** — сервис не запущен |
| Запрос SMS-кода по телефону | ❌ FAIL | Страница недоступна |

> **Скриншот:** `screenshots/30_lk_home.png`

---

## Console Errors

### nssb-maximum.ru (публичный сайт)
```
[error] A bad HTTP response code (404) was received when fetching the script.
[error] Failed to load resource: the server responded with a status of 404 (Not Found)
```
> Один JS-файл возвращает 404. Возможно, старый Service Worker или устаревший chunk-файл после деплоя.

### crm.nssb-maximum.ru
```
[error] Access to fetch at 'https://api.nssb-maximum.ru/api/v1/analytics/summary' from origin 'https://crm.nssb-maximum.ru' has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header (появляется дважды)
[error] Failed to load resource: net::ERR_FAILED
[error] TypeError: Failed to fetch at l (dashboard/page-92a42cdb...)
[pageerror] Minified React error #418 (text hydration mismatch)
```
> Все ошибки вызваны 500 на `/analytics/summary`. Dashboard пытается fetch этот эндпоинт, получает Internal Server Error, CORS-заголовки не добавляются → `ERR_FAILED` → React не может гидрировать → ошибка #418.

### lk.nssb-maximum.ru
```
[error] Failed to load resource: the server responded with a status of 503
```
> Весь фронтенд ЛК недоступен.

---

## Итог

| | Значение |
|---|---|
| **API тесты** | 11 / 14 ✅ |
| **UI сценарии** | 8 / 17 ✅ |
| **Всего** | 19 / 31 |

---

## Критические блокеры

1. **🔴 ЛК клиента (lk.nssb-maximum.ru) — 503** — весь клиентский ЛК недоступен. Пользователи не могут войти и видеть статус своих дел.

2. **🔴 GET /api/v1/analytics/summary → 500** — ломает CRM Dashboard (17 JS-ошибок, React hydration fail). Каждый сотрудник видит сломанный дашборд.

3. **🔴 GET /api/v1/billing/templates → 500** — разбивает раздел выставления счетов/договоров. Невозможно работать с биллингом.

4. **🔴 GET /api/v1/prospects/ → 500** — раздел проспектов (лидогенерация) недоступен через API.

---

## Некритичные баги

5. **🟡 CRM: нет маршрута `/tasks`** — в middleware и UI ожидается `/tasks`, но страница не создана. Навигация редиректит на /login.

6. **🟡 CRM `/clients` теряет сессию при навигации** — после серии переходов cookie `staff_token` не восстанавливается. Вероятно, SameSite=Lax + server-side middleware конфликт или race condition.

7. **🟡 Публичный сайт: 404 на JS-скрипт** — один chunk-файл недоступен. Требует re-deploy или очистки кеша CDN.

8. **🟡 API: 307 redirect без сохранения Authorization** — GET `/cases` (без слеша) возвращает 307, при этом заголовок `Authorization` теряется. Следует добавить trailing slash во все клиентские вызовы или настроить `redirect_slashes=False` в FastAPI.

9. **🟡 Публичный сайт: нет HTML-формы заявки** — CTA-кнопки используют JS-события (AI-чат), но нет fallback-формы. Если JS не загрузится, пользователь не сможет оставить заявку.

10. **🟢 БД пустая** — seed-скрипт не был запущен. `/cases/`, `/clients/` возвращают пустые массивы. Необходимо запустить `python -m scripts.seed` на prod (или использовать demo-данные).

---

## Рекомендации к исправлению (приоритеты)

```
P0 — запустить ЛК: lk-frontend не задеплоен или контейнер упал
P0 — fix /analytics/summary 500: проверить db query / импорт
P0 — fix /billing/templates 500: проверить db connection в billing router
P0 — fix /prospects/ 500: проверить prospects router
P1 — создать страницу /tasks в CRM или исправить навигацию
P1 — диагностировать потерю staff_token cookie
P2 — re-deploy site-frontend для исправления 404 JS chunk
P2 — настроить trailing slash в FastAPI или обновить все фронт-запросы
```

---

*Сформировано автоматически · tests/e2e/REPORT.md*
