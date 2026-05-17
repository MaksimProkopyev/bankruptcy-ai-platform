import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from leadgen.routers import ai, leads, prospects, stats, webhooks

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Leadgen Service",
    description="НССБ «Максимум» — сервис лидогенерации",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
app.include_router(leads.router, prefix="/api/v1/leads", tags=["leads"])
app.include_router(prospects.router, prefix="/api/v1/prospects", tags=["prospects"])
app.include_router(ai.router, prefix="/api/v1/ai", tags=["ai"])
app.include_router(stats.router, prefix="/api/v1", tags=["stats"])


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "leadgen"}
