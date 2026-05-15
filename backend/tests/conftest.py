"""Test fixtures."""

import os
import subprocess
import sys
from pathlib import Path
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import get_db
from app.main import app
from app.models import billing_models, cabinet_models, lead_models  # noqa: F401

TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/bankruptcy_ai_test",
)
BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = BACKEND_DIR.parent


def _run_alembic(command_name: str, target: str) -> None:
    script = (
        "import os, sys; "
        "backend = os.environ['BACKEND_DIR']; "
        "import alembic.config; "
        "sys.path.insert(0, backend); "
        "os.chdir(backend); "
        f"alembic.config.main(argv=['-c', 'alembic.ini', '{command_name}', '{target}'])"
    )
    env = os.environ.copy()
    env["BACKEND_DIR"] = str(BACKEND_DIR)
    env["ALEMBIC_DATABASE_URL"] = TEST_DB_URL
    subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(REPO_DIR),
        env=env,
        check=True,
    )


@pytest.fixture(scope="session", autouse=True)
def migrated_test_db() -> AsyncGenerator[None, None]:
    """Apply latest Alembic schema once per session."""
    _run_alembic("upgrade", "head")
    try:
        yield
    finally:
        if os.getenv("TEST_DB_DOWNGRADE_ON_EXIT") == "1":
            _run_alembic("downgrade", "base")


async def _truncate_all_tables(engine) -> None:
    """Clean database state between tests while keeping migrated schema.

    Excludes seed tables that are populated by migrations and should not be wiped.
    """
    # Tables populated by migration seeds that must be preserved across tests
    seed_tables = {"prospect_sources_config"}

    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                """
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public' AND tablename <> 'alembic_version'
                ORDER BY tablename
                """
            )
        )
        table_names = [row[0] for row in result.fetchall() if row[0] not in seed_tables]
        if table_names:
            joined = ", ".join(f'"{name}"' for name in table_names)
            await conn.execute(text(f"TRUNCATE TABLE {joined} RESTART IDENTITY CASCADE"))


@pytest_asyncio.fixture
async def db_session(migrated_test_db: None) -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(TEST_DB_URL, echo=False)
    test_session_local = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    await _truncate_all_tables(engine)
    async with test_session_local() as session:
        yield session
        await session.rollback()
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_headers(client: AsyncClient) -> dict:
    """Seed the admin user and return valid JWT auth headers."""
    await client.post("/api/v1/auth/seed-admin")
    res = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@bankruptcy.ai", "password": "admin123"},
    )
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
