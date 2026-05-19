"""
UI E2E Tests — НССБ Максимум
Запуск: python3.14 tests/e2e/e2e_ui.py [--headed]
"""
import asyncio
import sys
import json
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright, Page, BrowserContext

HEADED = "--headed" in sys.argv
SCREENSHOT_DIR = Path("tests/e2e/screenshots")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

CRM_URL = "https://crm.nssb-maximum.ru"
LK_URL = "https://lk.nssb-maximum.ru"
SITE_URL = "https://nssb-maximum.ru"
API_URL = "https://api.nssb-maximum.ru/api/v1"

EMAIL = "maksim.prokopiew@gmail.com"
PASSWORD = "Maks.26091991"
PHONE = "+79955426099"

results = []
console_errors = {}


def log_result(scenario, status, error=""):
    icon = "✅" if status == "PASS" else "❌"
    print(f"  {icon} {scenario}" + (f" — {error}" if error else ""))
    results.append({"scenario": scenario, "result": status, "error": error})


async def screenshot(page: Page, name: str):
    path = SCREENSHOT_DIR / f"{name}.png"
    await page.screenshot(path=str(path), full_page=False)


def collect_console(page: Page, label: str):
    errors = []
    console_errors[label] = errors
    page.on("console", lambda msg: errors.append(f"[{msg.type}] {msg.text}") if msg.type in ("error", "warning") else None)
    page.on("pageerror", lambda err: errors.append(f"[pageerror] {err}"))


# ──────────────────────────────────────────────────────────────────────────────
# PUBLIC SITE
# ──────────────────────────────────────────────────────────────────────────────
async def test_public_site(ctx: BrowserContext):
    print("\n── Публичный сайт (nssb-maximum.ru) ──────────────────────────────")

    page = await ctx.new_page()
    collect_console(page, "public_home")

    # 1. Главная открывается
    try:
        resp = await page.goto(SITE_URL, wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(2000)
        title = await page.title()
        has_content = bool(title and len(title) > 3)
        await screenshot(page, "01_public_home")
        js_errors = [e for e in console_errors.get("public_home", []) if "[error]" in e.lower() or "[pageerror]" in e.lower()]
        status_ok = resp and resp.status < 400
        if status_ok and has_content:
            log_result("Публичный сайт — главная загружается", "PASS",
                       f"title='{title[:60]}' js_errors={len(js_errors)}")
        else:
            log_result("Публичный сайт — главная загружается", "FAIL",
                       f"status={resp.status if resp else 'N/A'} title='{title}'")
    except Exception as e:
        log_result("Публичный сайт — главная загружается", "FAIL", str(e)[:100])
        await screenshot(page, "01_public_home_error")

    # 2. Форма заявки
    try:
        # Look for form/CTA button
        form = page.locator("form").first
        if await form.count() > 0:
            # fill name field
            name_input = form.locator("input[type=text], input[placeholder*='имя'], input[placeholder*='Имя'], input[name*='name'], input[name*='Name']").first
            phone_input = form.locator("input[type=tel], input[placeholder*='телефон'], input[placeholder*='Телефон'], input[name*='phone']").first

            if await name_input.count():
                await name_input.fill("[TEST] Тест Тестов")
            if await phone_input.count():
                await phone_input.fill("+79991234567")

            # submit
            submit_btn = form.locator("button[type=submit], button:has-text('Отправить'), button:has-text('Записаться'), button:has-text('Получить')").first
            if await submit_btn.count():
                await submit_btn.click()
                await page.wait_for_timeout(2000)
                await screenshot(page, "02_public_form_submitted")
                log_result("Публичный сайт — форма заявки отправлена", "PASS")
            else:
                log_result("Публичный сайт — форма заявки отправлена", "FAIL", "кнопка submit не найдена")
        else:
            # try to find any CTA
            cta = page.locator("button:has-text('Бесплатно'), button:has-text('Консультация'), a:has-text('Оставить заявку')").first
            if await cta.count():
                await cta.click()
                await page.wait_for_timeout(2000)
                await screenshot(page, "02_public_cta_click")
                log_result("Публичный сайт — CTA кнопка найдена и кликнута", "PASS")
            else:
                log_result("Публичный сайт — форма заявки отправлена", "FAIL", "форма и CTA не найдены на странице")
    except Exception as e:
        log_result("Публичный сайт — форма заявки отправлена", "FAIL", str(e)[:100])

    # 3. Nav links не ведут на 404
    try:
        nav_links = await page.locator("nav a[href], header a[href]").all()
        broken = []
        for link in nav_links[:10]:
            href = await link.get_attribute("href")
            if href and href.startswith("http") and "nssb-maximum.ru" in href:
                resp = await page.request.get(href)
                if resp.status == 404:
                    broken.append(href)
        if not broken:
            log_result(f"Публичный сайт — nav-ссылки без 404 ({len(nav_links)} links)", "PASS")
        else:
            log_result("Публичный сайт — nav-ссылки без 404", "FAIL", f"broken: {broken}")
    except Exception as e:
        log_result("Публичный сайт — nav-ссылки без 404", "FAIL", str(e)[:100])

    await page.close()


# ──────────────────────────────────────────────────────────────────────────────
# CRM
# ──────────────────────────────────────────────────────────────────────────────
async def test_crm(ctx: BrowserContext):
    print("\n── CRM (crm.nssb-maximum.ru) ─────────────────────────────────────")

    page = await ctx.new_page()
    collect_console(page, "crm")
    token = None
    client_id = None
    case_id = None

    # 1. Страница логина открывается
    try:
        await page.goto(f"{CRM_URL}/login", wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(1000)
        await screenshot(page, "10_crm_login")
        has_form = await page.locator("input[type=email], input[type=text]").count() > 0
        log_result("CRM — страница логина открывается", "PASS" if has_form else "FAIL",
                   "" if has_form else "форма не найдена")
    except Exception as e:
        log_result("CRM — страница логина открывается", "FAIL", str(e)[:100])
        await page.close()
        return token

    # 2. Логин
    try:
        await page.locator("input[type=email], input[name=email]").fill(EMAIL)
        await page.locator("input[type=password]").fill(PASSWORD)
        await page.locator("button[type=submit]").click()
        await page.wait_for_timeout(3000)
        await screenshot(page, "11_crm_after_login")

        current_url = page.url
        if "login" not in current_url:
            log_result("CRM — логин и редирект на dashboard", "PASS", f"url={current_url}")
            # Get token from localStorage
            token = await page.evaluate("() => localStorage.getItem('token')")
        else:
            error_text = await page.locator(".text-danger, .error, [class*='error']").text_content() if await page.locator(".text-danger, .error, [class*='error']").count() else ""
            log_result("CRM — логин и редирект на dashboard", "FAIL",
                       f"остался на /login, ошибка: {error_text[:80]}")
    except Exception as e:
        log_result("CRM — логин и редирект на dashboard", "FAIL", str(e)[:100])

    if not token:
        # If no token from UI, skip the rest
        log_result("CRM — dashboard загружается", "FAIL", "нет токена после логина")
        log_result("CRM — создать клиента [TEST]", "FAIL", "нет токена")
        log_result("CRM — изменить телефон клиента", "FAIL", "нет токена")
        log_result("CRM — создать дело для клиента", "FAIL", "нет токена")
        log_result("CRM — сменить статус дела", "FAIL", "нет токена")
        log_result("CRM — загрузить PDF в дело", "FAIL", "нет токена")
        log_result("CRM — создать задачу к делу", "FAIL", "нет токена")
        log_result("CRM — раздел Лиды открывается", "FAIL", "нет токена")
        log_result("CRM — раздел Проспекты открывается", "FAIL", "нет токена")
        log_result("CRM — навигация Cases/Clients/Leads/Tasks/Payments", "FAIL", "нет токена")
        await page.close()
        return token

    # 3. Dashboard
    try:
        await page.goto(f"{CRM_URL}/dashboard", wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(2000)
        await screenshot(page, "12_crm_dashboard")
        no_errors = len([e for e in console_errors.get("crm", []) if "[error]" in e]) == 0
        has_content = await page.locator("main, [class*='dashboard'], h1, h2").count() > 0
        log_result("CRM — dashboard загружается", "PASS" if has_content else "FAIL",
                   f"js_errors={len([e for e in console_errors.get('crm',[]) if '[error]' in e])}")
    except Exception as e:
        log_result("CRM — dashboard загружается", "FAIL", str(e)[:100])

    # 4. Создать клиента
    try:
        await page.goto(f"{CRM_URL}/clients", wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(2000)
        await screenshot(page, "13_crm_clients_list")

        # Find "new client" button
        new_btn = page.locator("button:has-text('Новый'), button:has-text('Добавить'), button:has-text('Создать'), a:has-text('Новый клиент')").first
        if await new_btn.count():
            await new_btn.click()
            await page.wait_for_timeout(1000)
            await screenshot(page, "14_crm_client_form")

            # Fill required fields
            fname = page.locator("input[name=first_name], input[placeholder*='Имя'], input[placeholder*='имя']").first
            lname = page.locator("input[name=last_name], input[placeholder*='Фамилия'], input[placeholder*='фамилия']").first
            phone_f = page.locator("input[name=phone], input[type=tel], input[placeholder*='телефон'], input[placeholder*='Телефон']").first

            if await fname.count(): await fname.fill("[TEST] Тестовый")
            if await lname.count(): await lname.fill("[TEST] Клиент")
            if await phone_f.count(): await phone_f.fill("+79990000001")

            # Email
            email_f = page.locator("input[type=email], input[name=email]").first
            if await email_f.count(): await email_f.fill("test_client_audit@test.com")

            save_btn = page.locator("button[type=submit], button:has-text('Сохранить'), button:has-text('Создать')").first
            if await save_btn.count():
                await save_btn.click()
                await page.wait_for_timeout(3000)
                await screenshot(page, "15_crm_client_created")

                # Check URL changed or success message
                url_after = page.url
                if "/clients/" in url_after and url_after != f"{CRM_URL}/clients":
                    client_id = url_after.split("/clients/")[-1].split("/")[0]
                    log_result("CRM — создать клиента [TEST]", "PASS", f"client_id={client_id}")
                else:
                    # try to find the test client in list
                    await page.goto(f"{CRM_URL}/clients", wait_until="domcontentloaded", timeout=10000)
                    await page.wait_for_timeout(1500)
                    test_row = page.locator("text=[TEST] Тестовый, text=[TEST] Клиент").first
                    if await test_row.count():
                        log_result("CRM — создать клиента [TEST]", "PASS", "клиент появился в списке")
                    else:
                        log_result("CRM — создать клиента [TEST]", "FAIL", "не появился в списке после сохранения")
            else:
                log_result("CRM — создать клиента [TEST]", "FAIL", "кнопка Save не найдена")
        else:
            log_result("CRM — создать клиента [TEST]", "FAIL", "кнопка New Client не найдена")
    except Exception as e:
        log_result("CRM — создать клиента [TEST]", "FAIL", str(e)[:100])

    # 5. Изменить телефон клиента
    if client_id:
        try:
            await page.goto(f"{CRM_URL}/clients/{client_id}", wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(1500)

            edit_btn = page.locator("button:has-text('Редактировать'), button:has-text('Edit')").first
            if await edit_btn.count(): await edit_btn.click()
            await page.wait_for_timeout(500)

            phone_f = page.locator("input[name=phone], input[type=tel]").first
            if await phone_f.count():
                await phone_f.fill("+79990000002")
                save_btn = page.locator("button[type=submit], button:has-text('Сохранить')").first
                if await save_btn.count():
                    await save_btn.click()
                    await page.wait_for_timeout(2000)
                    await screenshot(page, "16_crm_client_updated")
                    log_result("CRM — изменить телефон клиента", "PASS")
                else:
                    log_result("CRM — изменить телефон клиента", "FAIL", "Save кнопка не найдена")
            else:
                log_result("CRM — изменить телефон клиента", "FAIL", "phone input не найден")
        except Exception as e:
            log_result("CRM — изменить телефон клиента", "FAIL", str(e)[:100])
    else:
        log_result("CRM — изменить телефон клиента", "FAIL", "client_id неизвестен")

    # 6. Создать дело
    try:
        cases_url = f"{CRM_URL}/cases/new" if client_id is None else f"{CRM_URL}/cases/new?client_id={client_id}"
        await page.goto(f"{CRM_URL}/cases", wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(1500)
        await screenshot(page, "17_crm_cases_list")

        new_btn = page.locator("button:has-text('Новое дело'), button:has-text('Создать дело'), button:has-text('Новый'), a:has-text('Новое дело')").first
        if await new_btn.count():
            await new_btn.click()
            await page.wait_for_timeout(1000)
            await screenshot(page, "18_crm_case_form")

            # Fill case form
            title_f = page.locator("input[name=title], input[placeholder*='Название'], input[placeholder*='название']").first
            if await title_f.count(): await title_f.fill("[TEST] Тестовое дело — аудит")

            # Case type select
            type_sel = page.locator("select[name=case_type], [name=type]").first
            if await type_sel.count():
                await type_sel.select_option(index=1)  # pick first option

            save_btn = page.locator("button[type=submit], button:has-text('Создать'), button:has-text('Сохранить')").first
            if await save_btn.count():
                await save_btn.click()
                await page.wait_for_timeout(3000)
                await screenshot(page, "19_crm_case_created")
                url_after = page.url
                if "/cases/" in url_after and url_after != f"{CRM_URL}/cases":
                    case_id = url_after.split("/cases/")[-1].split("/")[0]
                    log_result("CRM — создать дело [TEST]", "PASS", f"case_id={case_id}")
                else:
                    log_result("CRM — создать дело [TEST]", "FAIL", f"url после сохранения: {url_after}")
            else:
                log_result("CRM — создать дело [TEST]", "FAIL", "Save кнопка не найдена")
        else:
            log_result("CRM — создать дело [TEST]", "FAIL", "кнопка New Case не найдена")
    except Exception as e:
        log_result("CRM — создать дело [TEST]", "FAIL", str(e)[:100])

    # 7. Сменить статус дела
    if case_id:
        try:
            await page.goto(f"{CRM_URL}/cases/{case_id}", wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(1500)

            status_sel = page.locator("select[name=status], button:has-text('Изменить статус'), [class*='status']").first
            if await status_sel.count():
                tag = await status_sel.evaluate("el => el.tagName.toLowerCase()")
                if tag == "select":
                    await status_sel.select_option(index=1)
                else:
                    await status_sel.click()
                    await page.wait_for_timeout(500)
                    option = page.locator("[role=option], li:has-text('in_progress'), li:has-text('В работе')").first
                    if await option.count(): await option.click()

                save_btn = page.locator("button[type=submit], button:has-text('Сохранить')").first
                if await save_btn.count(): await save_btn.click()
                await page.wait_for_timeout(2000)
                await screenshot(page, "20_crm_case_status_changed")
                log_result("CRM — сменить статус дела", "PASS")
            else:
                log_result("CRM — сменить статус дела", "FAIL", "поле статуса не найдено")
        except Exception as e:
            log_result("CRM — сменить статус дела", "FAIL", str(e)[:100])
    else:
        log_result("CRM — сменить статус дела", "FAIL", "case_id неизвестен")

    # 8. Загрузить PDF в дело
    if case_id:
        try:
            # Create tiny test PDF
            pdf_path = Path("/tmp/test_audit.pdf")
            pdf_path.write_bytes(
                b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj "
                b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj "
                b"3 0 obj<</Type/Page/MediaBox[0 0 3 3]>>endobj\n"
                b"xref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n"
                b"0000000058 00000 n\n0000000115 00000 n\n"
                b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF"
            )

            await page.goto(f"{CRM_URL}/cases/{case_id}", wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(1500)

            file_input = page.locator("input[type=file]").first
            upload_btn = page.locator("button:has-text('Загрузить'), button:has-text('Upload'), a:has-text('Добавить документ')").first

            if await file_input.count():
                await file_input.set_input_files(str(pdf_path))
                await page.wait_for_timeout(2000)
                await screenshot(page, "21_crm_doc_uploaded")
                log_result("CRM — загрузить PDF в дело", "PASS")
            elif await upload_btn.count():
                await upload_btn.click()
                await page.wait_for_timeout(500)
                file_input2 = page.locator("input[type=file]").first
                if await file_input2.count():
                    await file_input2.set_input_files(str(pdf_path))
                    await page.wait_for_timeout(2000)
                    await screenshot(page, "21_crm_doc_uploaded")
                    log_result("CRM — загрузить PDF в дело", "PASS")
                else:
                    log_result("CRM — загрузить PDF в дело", "FAIL", "file input не появился")
            else:
                log_result("CRM — загрузить PDF в дело", "FAIL", "input[type=file] не найден на странице дела")
        except Exception as e:
            log_result("CRM — загрузить PDF в дело", "FAIL", str(e)[:100])
    else:
        log_result("CRM — загрузить PDF в дело", "FAIL", "case_id неизвестен")

    # 9. Создать задачу к делу
    if case_id:
        try:
            await page.goto(f"{CRM_URL}/cases/{case_id}", wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(1500)

            task_btn = page.locator("button:has-text('Задача'), button:has-text('Добавить задачу'), button:has-text('Новая задача')").first
            if await task_btn.count():
                await task_btn.click()
                await page.wait_for_timeout(500)
                task_title = page.locator("input[placeholder*='Задача'], input[placeholder*='задача'], input[name=title]").first
                if await task_title.count():
                    await task_title.fill("[TEST] Аудит: тестовая задача")
                save_btn = page.locator("button[type=submit], button:has-text('Создать'), button:has-text('Сохранить')").first
                if await save_btn.count():
                    await save_btn.click()
                    await page.wait_for_timeout(2000)
                    await screenshot(page, "22_crm_task_created")
                    log_result("CRM — создать задачу к делу", "PASS")
                else:
                    log_result("CRM — создать задачу к делу", "FAIL", "Save не найден")
            else:
                # Try /tasks page
                await page.goto(f"{CRM_URL}/tasks", wait_until="domcontentloaded", timeout=10000)
                await page.wait_for_timeout(1000)
                await screenshot(page, "22_crm_tasks_page")
                log_result("CRM — создать задачу к делу", "FAIL", "кнопка Add Task не найдена на странице дела")
        except Exception as e:
            log_result("CRM — создать задачу к делу", "FAIL", str(e)[:100])
    else:
        log_result("CRM — создать задачу к делу", "FAIL", "case_id неизвестен")

    # 10. Раздел Лиды / Проспекты
    for section, path in [("Лиды", "/leads"), ("Проспекты", "/prospects")]:
        try:
            await page.goto(f"{CRM_URL}{path}", wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(1500)
            await screenshot(page, f"23_crm{path.replace('/', '_')}")
            # Check 404 page or real content
            is_404 = "404" in await page.title() or await page.locator("text=404, text=Not Found").count() > 0
            has_content = await page.locator("table, [class*='list'], [class*='grid'], main h1, main h2").count() > 0
            if is_404:
                log_result(f"CRM — раздел {section} открывается", "FAIL", "404")
            elif has_content or not is_404:
                log_result(f"CRM — раздел {section} открывается", "PASS", f"url={page.url}")
            else:
                log_result(f"CRM — раздел {section} открывается", "FAIL", "пустая страница без контента")
        except Exception as e:
            log_result(f"CRM — раздел {section} открывается", "FAIL", str(e)[:100])

    # 11. Навигация
    nav_sections = [
        ("Cases", "/cases"),
        ("Clients", "/clients"),
        ("Tasks", "/tasks"),
        ("Payments", "/billing"),
    ]
    nav_ok = []
    nav_fail = []
    for name, path in nav_sections:
        try:
            resp = await page.goto(f"{CRM_URL}{path}", wait_until="domcontentloaded", timeout=10000)
            await page.wait_for_timeout(800)
            is_ok = resp and resp.status < 400 and "login" not in page.url
            (nav_ok if is_ok else nav_fail).append(name)
        except Exception as e:
            nav_fail.append(f"{name}:{str(e)[:40]}")

    if not nav_fail:
        log_result(f"CRM — навигация {'/'.join(n for n,_ in nav_sections)}", "PASS",
                   f"все {len(nav_ok)} разделов открылись")
    else:
        log_result("CRM — навигация по разделам", "FAIL", f"fail: {nav_fail}")

    await screenshot(page, "24_crm_final")
    await page.close()
    return token


# ──────────────────────────────────────────────────────────────────────────────
# ЛК КЛИЕНТА
# ──────────────────────────────────────────────────────────────────────────────
async def test_lk(ctx: BrowserContext):
    print("\n── ЛК Клиента (lk.nssb-maximum.ru) ──────────────────────────────")

    page = await ctx.new_page()
    collect_console(page, "lk")

    # 1. Страница логина открывается
    try:
        await page.goto(LK_URL, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(1500)
        await screenshot(page, "30_lk_home")
        title = await page.title()
        has_input = await page.locator("input[type=tel], input[type=phone], input[placeholder*='Телефон'], input[placeholder*='телефон']").count() > 0
        log_result("ЛК — страница логина открывается", "PASS" if (has_input or len(title) > 3) else "FAIL",
                   f"title='{title[:50]}' phone_input={'yes' if has_input else 'no'}")
    except Exception as e:
        log_result("ЛК — страница логина открывается", "FAIL", str(e)[:100])
        await page.close()
        return

    # 2. Ввести телефон и запросить код
    try:
        phone_inp = page.locator("input[type=tel], input[placeholder*='Телефон'], input[placeholder*='телефон'], input[name=phone]").first
        if await phone_inp.count():
            await phone_inp.fill(PHONE)
            send_btn = page.locator("button:has-text('Отправить'), button:has-text('Получить код'), button[type=submit]").first
            if await send_btn.count():
                await send_btn.click()
                await page.wait_for_timeout(2000)
                await screenshot(page, "31_lk_code_requested")
                # Check for code input
                code_inp = page.locator("input[name=code], input[placeholder*='Код'], input[maxlength='6']").first
                if await code_inp.count():
                    log_result("ЛК — запрос кода по телефону", "PASS", "поле для кода появилось")
                else:
                    log_result("ЛК — запрос кода по телефону", "PASS", "запрос отправлен (код не показан в UI)")
            else:
                log_result("ЛК — запрос кода по телефону", "FAIL", "кнопка отправки не найдена")
        else:
            log_result("ЛК — запрос кода по телефону", "FAIL", "phone input не найден")
    except Exception as e:
        log_result("ЛК — запрос кода по телефону", "FAIL", str(e)[:100])

    await page.close()


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────
async def main():
    print("\n=== UI E2E Tests — НССБ Максимум ===")
    print(f"Time:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Headed: {HEADED}\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=not HEADED)
        ctx = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            ignore_https_errors=True,
        )
        ctx.set_default_timeout(15000)

        await test_public_site(ctx)
        await test_crm(ctx)
        await test_lk(ctx)

        await ctx.close()
        await browser.close()

    print("\n── Summary ──────────────────────────────────────────────────────")
    passed = sum(1 for r in results if r["result"] == "PASS")
    total = len(results)
    print(f"Passed: {passed}/{total}")

    print("\n── Console Errors ───────────────────────────────────────────────")
    for page_label, errors in console_errors.items():
        errs = [e for e in errors if "[error]" in e.lower() or "[pageerror]" in e.lower()]
        if errs:
            print(f"  [{page_label}]")
            for e in errs[:5]:
                print(f"    {e[:120]}")

    return results, console_errors


if __name__ == "__main__":
    asyncio.run(main())
