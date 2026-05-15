"""Fixtures for completeness tests."""

from __future__ import annotations

import uuid

import pytest_asyncio

from app.core.security import create_access_token
from app.models.case_checklist_item import CaseChecklistItem, ChecklistItemStatus
from app.models.models import Case, Client, Document, User


@pytest_asyncio.fixture
async def test_lawyer(db_session) -> User:
    """Тестовый юрист."""
    user = User(
        id=uuid.uuid4(),
        email="lawyer@test.com",
        role="lawyer",
        first_name="Тестовый",
        last_name="Юрист",
        password_hash="hashed",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def test_client_user(db_session) -> User:
    """Тестовый пользователь-клиент."""
    user = User(
        id=uuid.uuid4(),
        email="client@test.com",
        role="client",
        first_name="Иван",
        last_name="Иванов",
        password_hash="hashed",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def test_client(db_session, test_client_user) -> Client:
    """Тестовая карточка клиента."""
    client = Client(
        id=uuid.uuid4(),
        first_name="Иван",
        last_name="Иванов",
        patronymic="Иванович",
        phone="+79991234567",
        email="client@test.com",
    )
    db_session.add(client)
    await db_session.commit()
    return client


@pytest_asyncio.fixture
async def test_case(db_session, test_client, test_lawyer) -> Case:
    """Тестовое дело (судебное банкротство физлица)."""
    case = Case(
        id=uuid.uuid4(),
        client_id=test_client.id,
        case_number="А60-12345/2026",
        status="lead",
        procedure_type="extrajudicial",  # будет использоваться для определения чеклиста
        assigned_lawyer_id=test_lawyer.id,
    )
    db_session.add(case)
    await db_session.commit()
    return case


@pytest_asyncio.fixture
async def test_case_ip(db_session, test_client, test_lawyer) -> Case:
    """Тестовое дело (ИП)."""
    case = Case(
        id=uuid.uuid4(),
        client_id=test_client.id,
        case_number="А60-67890/2026",
        status="lead",
        procedure_type="asset_realization",  # судебная процедура
        assigned_lawyer_id=test_lawyer.id,
    )
    db_session.add(case)
    await db_session.commit()
    return case


@pytest_asyncio.fixture
async def test_documents(db_session, test_case, test_client_user) -> list[Document]:
    """Набор тестовых документов для auto-match."""
    docs = [
        Document(
            id=uuid.uuid4(),
            case_id=test_case.id,
            document_type="passport",
            file_name="passport_scan.pdf",
            file_path="/uploads/passport_scan.pdf",
            mime_type="application/pdf",
            uploaded_by=test_client_user.id,
        ),
        Document(
            id=uuid.uuid4(),
            case_id=test_case.id,
            document_type=None,  # тип не указан — для fuzzy match
            file_name="снилс_иванов.jpg",
            file_path="/uploads/snils.jpg",
            mime_type="image/jpeg",
            uploaded_by=test_client_user.id,
        ),
        Document(
            id=uuid.uuid4(),
            case_id=test_case.id,
            document_type=None,
            file_name="справка_2ндфл_2025.pdf",
            file_path="/uploads/2ndfl.pdf",
            mime_type="application/pdf",
            uploaded_by=test_client_user.id,
        ),
        Document(
            id=uuid.uuid4(),
            case_id=test_case.id,
            document_type=None,
            file_name="random_photo.jpg",
            file_path="/uploads/random.jpg",
            mime_type="image/jpeg",
            uploaded_by=test_client_user.id,
        ),
    ]
    db_session.add_all(docs)
    await db_session.commit()
    return docs


@pytest_asyncio.fixture
async def test_checklist_items(db_session, test_case) -> list[CaseChecklistItem]:
    """Тестовые checklist items для дела."""
    items = [
        CaseChecklistItem(
            id=uuid.uuid4(),
            case_id=test_case.id,
            checklist_id="individual_extrajudicial",
            checklist_item_id="passport_main",
            status=ChecklistItemStatus.MISSING,
        ),
        CaseChecklistItem(
            id=uuid.uuid4(),
            case_id=test_case.id,
            checklist_id="individual_extrajudicial",
            checklist_item_id="snils",
            status=ChecklistItemStatus.UPLOADED,
            document_id=uuid.uuid4(),  # placeholder
        ),
        CaseChecklistItem(
            id=uuid.uuid4(),
            case_id=test_case.id,
            checklist_id="individual_extrajudicial",
            checklist_item_id="income_2ndfl",
            status=ChecklistItemStatus.APPROVED,
            document_id=uuid.uuid4(),
            reviewer_id=uuid.uuid4(),
        ),
    ]
    db_session.add_all(items)
    await db_session.commit()
    return items


@pytest_asyncio.fixture
async def auth_headers(test_lawyer) -> dict:
    """Auth headers для юриста — генерирует реальный JWT токен."""
    token = create_access_token(test_lawyer.id, test_lawyer.role)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def client_auth_headers(test_client_user) -> dict:
    """Auth headers для клиента — генерирует реальный JWT токен."""
    token = create_access_token(test_client_user.id, test_client_user.role)
    return {"Authorization": f"Bearer {token}"}
