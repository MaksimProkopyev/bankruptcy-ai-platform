"""API v1 router — all endpoints."""

from fastapi import APIRouter

from app.api.v1 import (
    ai,
    analytics,
    anticollector,
    auth,
    billing,
    cases,
    client_auth,
    client_cabinet,
    clients,
    completeness,
    documents,
    lead_sources,
    notifications,
    prospects,
    staff,
    users,
)

api_router = APIRouter()

# Staff endpoints
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(clients.router, prefix="/clients", tags=["clients"])
api_router.include_router(cases.router, prefix="/cases", tags=["cases"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(billing.router, prefix="/billing", tags=["billing"])
api_router.include_router(lead_sources.router, prefix="/lead-sources", tags=["lead-sources"])
api_router.include_router(prospects.router, prefix="/prospects", tags=["prospects"])
api_router.include_router(completeness.router, tags=["completeness"])

# Staff personal cabinet
api_router.include_router(staff.router, prefix="/staff", tags=["staff"])

# Client personal cabinet
api_router.include_router(client_auth.router, prefix="/client-auth", tags=["client-auth"])
api_router.include_router(client_cabinet.router, prefix="/cabinet", tags=["client-cabinet"])

# Anticollector (public — no auth needed for registration)
api_router.include_router(anticollector.router, prefix="/anticollector", tags=["anticollector"])
