"""Tests for document checklist service."""

from app.services.document_checklist import get_required_documents, calculate_completeness


def test_base_documents_always_present():
    docs = get_required_documents()
    types = [d["type"] for d in docs]
    assert "passport" in types
    assert "snils" in types
    assert "inn_cert" in types
    assert "income_2ndfl" in types
    assert "credit_report" in types


def test_married_adds_marriage_cert():
    docs = get_required_documents(marital_status="married")
    types = [d["type"] for d in docs]
    assert "marriage_cert" in types


def test_divorced_adds_divorce_cert():
    docs = get_required_documents(marital_status="divorced")
    types = [d["type"] for d in docs]
    assert "divorce_cert" in types


def test_property_adds_egrn():
    docs = get_required_documents(has_property_types=["apartment"])
    types = [d["type"] for d in docs]
    assert "egrn_extract" in types


def test_car_adds_vehicle_title():
    docs = get_required_documents(has_property_types=["car"])
    types = [d["type"] for d in docs]
    assert "vehicle_title" in types


def test_completeness_calculation():
    docs = get_required_documents()
    required_types = {d["type"] for d in docs if d["required"]}

    # Nothing collected
    result = calculate_completeness(docs, set())
    assert result["collected"] == 0
    assert result["is_complete"] is False
    assert result["progress_percent"] == 0

    # All required collected
    result = calculate_completeness(docs, required_types)
    assert result["is_complete"] is True
    assert result["progress_percent"] == 100.0


def test_completeness_partial():
    docs = get_required_documents()
    result = calculate_completeness(docs, {"passport", "snils"})
    assert result["collected"] == 2
    assert result["is_complete"] is False
    assert 0 < result["progress_percent"] < 100
