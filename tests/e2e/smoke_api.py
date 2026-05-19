"""
API Smoke Tests — НССБ Максимум
Запуск: python tests/e2e/smoke_api.py
"""
import httpx
import json
from datetime import datetime

BASE = "https://api.nssb-maximum.ru"
API = f"{BASE}/api/v1"

EMAIL = "maksim.prokopiew@gmail.com"
PASSWORD = "Maks.26091991"
PHONE = "+79955426099"

results = []


def log(endpoint, status, result, note=""):
    icon = "✅" if result == "OK" else "❌"
    print(f"  {icon} [{status}] {endpoint}" + (f" — {note}" if note else ""))
    results.append({"endpoint": endpoint, "status": status, "result": result, "note": note})


def count_note(body):
    if isinstance(body, list):
        return f"count={len(body)}"
    if isinstance(body, dict):
        for k in ("total", "count", "items", "data"):
            if k in body:
                v = body[k]
                return f"{k}={len(v) if isinstance(v, list) else v}"
        return f"keys={list(body.keys())[:5]}"
    return "(non-json)"


def run():
    token = None

    print("\n=== API Smoke Tests — НССБ Максимум ===\n")
    print(f"Target: {BASE}")
    print(f"Time:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    with httpx.Client(timeout=20, follow_redirects=True) as c:

        # ── 1. Health ──────────────────────────────────────────────────────
        try:
            r = c.get(f"{BASE}/health")
            body = r.json()
            ok = r.status_code == 200 and body.get("status") == "ok"
            log("GET /health", r.status_code, "OK" if ok else "FAIL",
                f"version={body.get('version','?')}" if ok else json.dumps(body)[:120])
        except Exception as e:
            log("GET /health", "ERROR", "FAIL", str(e)[:120])

        # ── 2. Staff login (JSON body) ──────────────────────────────────────
        try:
            r = c.post(f"{API}/auth/login",
                       json={"email": EMAIL, "password": PASSWORD})
            if r.status_code == 200:
                body = r.json()
                token = body.get("access_token")
                log("POST /auth/login", r.status_code, "OK" if token else "FAIL",
                    f"token={'present' if token else 'missing'}")
            else:
                log("POST /auth/login", r.status_code, "FAIL", r.text[:150])
        except Exception as e:
            log("POST /auth/login", "ERROR", "FAIL", str(e)[:120])

        if not token:
            print("\n⚠️  No token — authenticated endpoints will FAIL\n")

        auth = {"Authorization": f"Bearer {token}"} if token else {}

        # ── 3. GET /auth/me ────────────────────────────────────────────────
        try:
            r = c.get(f"{API}/auth/me", headers=auth)
            ok = r.status_code == 200
            if ok:
                b = r.json()
                note = f"id={b.get('id','?')} role={b.get('role','?')} email={b.get('email','?')}"
            else:
                note = r.text[:120]
            log("GET /auth/me", r.status_code, "OK" if ok else "FAIL", note)
        except Exception as e:
            log("GET /auth/me", "ERROR", "FAIL", str(e)[:120])

        # ── 4. Cases ───────────────────────────────────────────────────────
        try:
            r = c.get(f"{API}/cases/", headers=auth)
            ok = r.status_code == 200
            log("GET /cases/", r.status_code, "OK" if ok else "FAIL",
                count_note(r.json()) if ok else r.text[:120])
        except Exception as e:
            log("GET /cases/", "ERROR", "FAIL", str(e)[:120])

        # ── 5. Clients ─────────────────────────────────────────────────────
        try:
            r = c.get(f"{API}/clients/", headers=auth)
            ok = r.status_code == 200
            log("GET /clients/", r.status_code, "OK" if ok else "FAIL",
                count_note(r.json()) if ok else r.text[:120])
        except Exception as e:
            log("GET /clients/", "ERROR", "FAIL", str(e)[:120])

        # ── 6. Prospects (leads) ───────────────────────────────────────────
        try:
            r = c.get(f"{API}/prospects/", headers=auth)
            ok = r.status_code == 200
            log("GET /prospects/", r.status_code, "OK" if ok else "FAIL",
                count_note(r.json()) if ok else r.text[:120])
        except Exception as e:
            log("GET /prospects/", "ERROR", "FAIL", str(e)[:120])

        # ── 7. Staff tasks ────────────────────────────────────────────────
        try:
            r = c.get(f"{API}/staff/me/tasks", headers=auth)
            ok = r.status_code == 200
            log("GET /staff/me/tasks", r.status_code, "OK" if ok else "FAIL",
                count_note(r.json()) if ok else r.text[:120])
        except Exception as e:
            log("GET /staff/me/tasks", "ERROR", "FAIL", str(e)[:120])

        # ── 8. Analytics summary ──────────────────────────────────────────
        try:
            r = c.get(f"{API}/analytics/summary", headers=auth)
            ok = r.status_code == 200
            log("GET /analytics/summary", r.status_code, "OK" if ok else "FAIL",
                count_note(r.json()) if ok else r.text[:120])
        except Exception as e:
            log("GET /analytics/summary", "ERROR", "FAIL", str(e)[:120])

        # ── 9. Library (document knowledge base) ──────────────────────────
        try:
            r = c.get(f"{API}/library/", headers=auth)
            ok = r.status_code == 200
            log("GET /library/", r.status_code, "OK" if ok else "FAIL",
                count_note(r.json()) if ok else r.text[:120])
        except Exception as e:
            log("GET /library/", "ERROR", "FAIL", str(e)[:120])

        # ── 10. Billing templates ──────────────────────────────────────────
        try:
            r = c.get(f"{API}/billing/templates", headers=auth)
            ok = r.status_code == 200
            log("GET /billing/templates", r.status_code, "OK" if ok else "FAIL",
                count_note(r.json()) if ok else r.text[:120])
        except Exception as e:
            log("GET /billing/templates", "ERROR", "FAIL", str(e)[:120])

        # ── 11. Analytics funnel ───────────────────────────────────────────
        try:
            r = c.get(f"{API}/analytics/funnel", headers=auth)
            ok = r.status_code == 200
            log("GET /analytics/funnel", r.status_code, "OK" if ok else "FAIL",
                count_note(r.json()) if ok else r.text[:120])
        except Exception as e:
            log("GET /analytics/funnel", "ERROR", "FAIL", str(e)[:120])

        # ── 12. Client-auth send-code ─────────────────────────────────────
        try:
            r = c.post(f"{API}/client-auth/send-code", json={"phone": PHONE})
            ok = r.status_code == 200
            log("POST /client-auth/send-code", r.status_code,
                "OK" if ok else "FAIL", r.text[:80])
        except Exception as e:
            log("POST /client-auth/send-code", "ERROR", "FAIL", str(e)[:120])

    print("\n── Summary ──────────────────────────────────────────────────────")
    passed = sum(1 for r in results if r["result"] == "OK")
    total = len(results)
    print(f"Passed: {passed}/{total}\n")
    return results


if __name__ == "__main__":
    run()
