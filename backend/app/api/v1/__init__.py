"""API v1 routers."""

from fastapi import APIRouter

from .auth import router as auth_router
from .users import router as users_router
from .clients import router as clients_router
from .cases import router as cases_router
from .documents import router as documents_router
from .ai import router as ai_router
from .analytics import router as analytics_router
from .notifications import router as notifications_router
from .client_auth import router as client_auth_router
from .client_cabinet import router as client_cabinet_router
from .anticollector import router as anticollector_router
from .billing import router as billing_router
from .lead_sources import router as lead_sources_router
from .prospects import router as prospects_router
from .completeness import router as completeness_router

api_router = APIRouter(prefix="/api/v1")

# Staff endpoints
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(clients_router, prefix="/clients", tags=["clients"])
api_router.include_router(cases_router, prefix="/cases", tags=["cases"])
api_router.include_router(documents_router, prefix="/documents", tags=["documents"])
api_router.include_router(ai_router, prefix="/ai", tags=["ai"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
api_router.include_router(notifications_router, prefix="/notifications", tags=["notifications"])
api_router.include_router(billing_router, prefix="/billing", tags=["billing"])
api_router.include_router(lead_sources_router, prefix="/lead-sources", tags=["lead-sources"])
api_router.include_router(prospects_router, prefix="/prospects", tags=["prospects"])
api_router.include_router(completeness_router, tags=["completeness"])

# Client personal cabinet
api_router.include_router(client_auth_router, prefix="/client-auth", tags=["client-auth"])
api_router.include_router(client_cabinet_router, prefix="/cabinet", tags=["client-cabinet"])

# Anticollector (public — no auth needed for registration)
api_router.include_router(anticollector_router, prefix="/anticollector", tags=["anticollector"])