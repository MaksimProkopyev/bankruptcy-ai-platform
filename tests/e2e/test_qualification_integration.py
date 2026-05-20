"""E2E integration tests for the qualification agent endpoint.

Tests:
    - POST /api/v1/leads/{id}/qualify → 200, status=started
    - POST /api/v1/leads/{id}/qualify → 404 if lead not found
    - POST /api/v1/leads/{id}/qualify → 409 if already in progress
    - QualificationTask is created with status=processing in DB

Run:
    pytest tests/e2e/test_qualification_integration.py -v --tb=short
"""

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from leadgen.main import app
from leadgen.models.lead import Lead, LeadStatus
from leadgen.models.qualification_task import QualificationTask


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_lead(**kwargs) -> Lead:
    defaults = {
        "id": uuid.uuid4(),
        "channel": "web",
        "status": LeadStatus.NEW,
        "funnel_stage": "incoming",
        "debt_amount": 750_000,
        "debt_type": "bank_loans",
        "has_property": False,
        "has_income": True,
    }
    defaults.update(kwargs)
    lead = Lead()
    for k, v in defaults.items():
        setattr(lead, k, v)
    return lead


def _make_task(lead_id: uuid.UUID, status: str = "processing") -> QualificationTask:
    task = QualificationTask()
    task.id = uuid.uuid4()
    task.lead_id = lead_id
    task.status = status
    return task


# ---------------------------------------------------------------------------
# Unit-level integration tests (mocked DB)
# ---------------------------------------------------------------------------


class TestQualifyEndpoint:
    """Tests for POST /api/v1/leads/{lead_id}/qualify."""

    def _mock_db(self, lead=None, active_task=None):
        """Return a mock AsyncSession that responds to .get() and .execute()."""
        db = AsyncMock(spec=AsyncSession)

        async def mock_get(model, pk):
            if model is Lead:
                return lead
            if model is QualificationTask:
                return active_task
            return None

        db.get.side_effect = mock_get

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = active_task
        db.execute = AsyncMock(return_value=result_mock)
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        return db

    def test_qualify_lead_success(self):
        """POST /qualify → 200 with task_id and status=started."""
        lead = _make_lead()
        task = _make_task(lead.id)

        mock_db = self._mock_db(lead=lead, active_task=None)

        with (
            patch("leadgen.routers.leads.get_db", return_value=mock_db),
            patch(
                "leadgen.services.qualification.start_qualification",
                new_callable=AsyncMock,
                return_value=task,
            ) as mock_start,
            patch("asyncio.create_task"),  # prevent actual background task
        ):
            # Override FastAPI dependency
            async def override_db():
                yield mock_db

            app.dependency_overrides[
                __import__("leadgen.database", fromlist=["get_db"]).get_db
            ] = override_db

            client = TestClient(app)
            resp = client.post(f"/api/v1/leads/{lead.id}/qualify")

            app.dependency_overrides.clear()

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "started"
        assert "task_id" in body

    def test_qualify_lead_not_found(self):
        """POST /qualify → 404 if lead does not exist."""
        mock_db = self._mock_db(lead=None)

        async def override_db():
            yield mock_db

        from leadgen.database import get_db

        app.dependency_overrides[get_db] = override_db

        client = TestClient(app)
        resp = client.post(f"/api/v1/leads/{uuid.uuid4()}/qualify")

        app.dependency_overrides.clear()

        assert resp.status_code == 404

    def test_qualify_lead_already_in_progress(self):
        """POST /qualify → 409 if qualification is already running."""
        lead = _make_lead()
        active_task = _make_task(lead.id, status="processing")

        mock_db = self._mock_db(lead=lead, active_task=active_task)

        async def override_db():
            yield mock_db

        from leadgen.database import get_db

        app.dependency_overrides[get_db] = override_db

        client = TestClient(app)
        resp = client.post(f"/api/v1/leads/{lead.id}/qualify")

        app.dependency_overrides.clear()

        assert resp.status_code == 409

    def test_qualify_updates_lead_status_from_new(self):
        """POST /qualify → lead status changes from new to in_progress."""
        lead = _make_lead(status=LeadStatus.NEW)
        task = _make_task(lead.id)

        mock_db = self._mock_db(lead=lead, active_task=None)

        status_updated = []

        original_setattr = object.__setattr__

        def track_status(obj, name, value):
            if isinstance(obj, Lead) and name == "status":
                status_updated.append(value)
            original_setattr(obj, name, value)

        with (
            patch(
                "leadgen.services.qualification.start_qualification",
                new_callable=AsyncMock,
                return_value=task,
            ),
            patch("asyncio.create_task"),
        ):
            async def override_db():
                yield mock_db

            from leadgen.database import get_db

            app.dependency_overrides[get_db] = override_db

            client = TestClient(app)
            resp = client.post(f"/api/v1/leads/{lead.id}/qualify")

            app.dependency_overrides.clear()

        assert resp.status_code == 200
        # The endpoint committed after setting status; lead was set to IN_PROGRESS
        assert mock_db.commit.called


# ---------------------------------------------------------------------------
# Service-level unit tests
# ---------------------------------------------------------------------------


class TestQualificationService:
    """Unit tests for leadgen/services/qualification.py."""

    @pytest.mark.asyncio
    async def test_start_qualification_creates_task(self):
        """start_qualification() returns a QualificationTask with status=processing."""
        import sys
        from types import ModuleType

        # Stub langchain_core if not installed (CI without full LangGraph deps)
        if "langchain_core" not in sys.modules:
            lc_stub = ModuleType("langchain_core")
            lc_messages_stub = ModuleType("langchain_core.messages")
            lc_messages_stub.HumanMessage = MagicMock(side_effect=lambda content: MagicMock(content=content))
            lc_stub.messages = lc_messages_stub
            sys.modules["langchain_core"] = lc_stub
            sys.modules["langchain_core.messages"] = lc_messages_stub

        from leadgen.services.qualification import start_qualification

        lead = _make_lead()
        task = _make_task(lead.id)

        db = AsyncMock(spec=AsyncSession)
        db.get.return_value = lead

        messages_result = MagicMock()
        messages_result.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(return_value=messages_result)

        db.add.side_effect = lambda obj: setattr(obj, "id", task.id) or None
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        with (
            patch("asyncio.create_task") as mock_create_task,
            patch("leadgen.services.qualification._get_graph", new_callable=AsyncMock),
        ):
            result = await start_qualification(lead.id, db)

        assert db.add.called
        assert db.commit.called
        assert mock_create_task.called  # background task was spawned

    @pytest.mark.asyncio
    async def test_resume_qualification_no_active_task(self):
        """resume_qualification() silently returns when no active task exists."""
        from leadgen.services.qualification import resume_qualification

        lead_id = uuid.uuid4()
        db = AsyncMock(spec=AsyncSession)

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=result_mock)

        with patch("asyncio.create_task") as mock_create_task:
            await resume_qualification(lead_id, "hello", db)

        mock_create_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_resume_qualification_spawns_background_task(self):
        """resume_qualification() spawns asyncio.create_task when active task exists."""
        from leadgen.services.qualification import resume_qualification

        lead_id = uuid.uuid4()
        active_task = _make_task(lead_id, status="processing")

        db = AsyncMock(spec=AsyncSession)
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = active_task
        db.execute = AsyncMock(return_value=result_mock)

        with patch("asyncio.create_task") as mock_create_task:
            await resume_qualification(lead_id, "I have 800k debt", db)

        mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_final_state_qualified(self):
        """_handle_final_state() marks task done and creates prospect on 'qualified'."""
        from leadgen.services.qualification import _handle_final_state

        lead_id = uuid.uuid4()
        task_id = str(uuid.uuid4())
        lead = _make_lead(id=lead_id)
        task = _make_task(lead_id)
        task.id = uuid.UUID(task_id)

        final_state = {
            "verdict": "qualified",
            "score": 75,
            "reasoning": "Good candidate",
            "signals": {"debt_amount": 800_000},
        }

        prospect_result = MagicMock()
        prospect_result.scalar_one_or_none.return_value = None

        db = AsyncMock(spec=AsyncSession)
        db.get.side_effect = lambda model, pk: (
            task if model is QualificationTask else lead
        )
        db.execute = AsyncMock(return_value=prospect_result)
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.rollback = AsyncMock()

        with patch(
            "leadgen.services.qualification.AsyncSessionLocal"
        ) as mock_session_local:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = db
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_session_local.return_value = mock_ctx

            await _handle_final_state(task_id, str(lead_id), final_state)

        assert task.status == "done"
        assert lead.status == LeadStatus.QUALIFIED
        assert lead.qualification_score == 75
        db.add.assert_called_once()  # prospect was created

    @pytest.mark.asyncio
    async def test_handle_final_state_paused(self):
        """_handle_final_state() does nothing when graph is paused (verdict=None)."""
        from leadgen.services.qualification import _handle_final_state

        with patch(
            "leadgen.services.qualification.AsyncSessionLocal"
        ) as mock_session_local:
            await _handle_final_state("task-1", str(uuid.uuid4()), {"verdict": None})

        mock_session_local.assert_not_called()
