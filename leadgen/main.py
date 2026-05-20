import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from leadgen.routers import ai, leads, prospects, stats, webhooks

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _setup_phoenix_tracing() -> None:
    """Initialize Arize Phoenix OTEL tracing (runs once at startup)."""
    endpoint = os.getenv("PHOENIX_ENDPOINT", "")
    if not endpoint:
        logger.info("PHOENIX_ENDPOINT not set — Phoenix tracing disabled")
        return
    try:
        from openinference.instrumentation.langchain import LangChainInstrumentor
        from phoenix.otel import register

        tracer_provider = register(
            project_name="qualification-agent",
            endpoint=endpoint,
        )
        LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
        logger.info("Phoenix tracing enabled → %s", endpoint)
    except Exception:
        logger.exception("Failed to initialize Phoenix tracing — continuing without it")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _setup_phoenix_tracing()
    yield


app = FastAPI(
    title="Leadgen Service",
    description="НССБ «Максимум» — сервис лидогенерации",
    version="1.0.0",
    lifespan=lifespan,
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
