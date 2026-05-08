"""Document checklist service.

Manages the checklist of required documents for each bankruptcy case.
Determines which documents are needed based on case type and client situation.
"""

from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import DocumentType


# Required documents for all bankruptcy cases
BASE_DOCUMENTS = [
    (DocumentType.passport, True, "Паспорт РФ (все страницы)"),
    (DocumentType.snils, True, "СНИЛС"),
    (DocumentType.inn_cert, True, "ИНН (свидетельство или справка)"),
    (DocumentType.income_2ndfl, True, "Справка 2-НДФЛ за 3 года"),
    (DocumentType.credit_report, True, "Кредитная история (отчёт БКИ)"),
    (DocumentType.bank_statement, True, "Выписки по всем счетам за 3 года"),
]

# Conditional documents
CONDITIONAL_DOCUMENTS = {
    "married": [
        ("marriage_cert", True, "Свидетельство о браке"),
    ],
    "divorced": [
        ("divorce_cert", True, "Свидетельство о расторжении брака"),
    ],
    "has_property_apartment": [
        (DocumentType.egrn_extract, True, "Выписка из ЕГРН (на квартиру/дом)"),
    ],
    "has_property_car": [
        (DocumentType.vehicle_title, True, "ПТС / СТС (на автомобиль)"),
    ],
    "unemployed": [
        ("unemployment_cert", True, "Справка из центра занятости"),
    ],
    "has_credits": [
        (DocumentType.credit_contract, True, "Кредитные договоры"),
        ("payment_schedule", False, "Графики платежей"),
    ],
}

# Documents generated during the process
PROCESS_DOCUMENTS = [
    (DocumentType.bankruptcy_application, True, "Заявление о банкротстве"),
    (DocumentType.creditors_registry, True, "Реестр кредиторов"),
    ("asset_inventory", True, "Опись имущества"),
    ("power_of_attorney", True, "Доверенность на представителя"),
]


def get_required_documents(
    marital_status: str | None = None,
    is_employed: bool | None = None,
    has_property_types: list[str] | None = None,
    creditors_count: int = 0,
) -> list[dict]:
    """Get the full document checklist for a case.
    
    Returns a list of dicts with: type, required, description, category.
    """
    checklist = []

    # Base documents
    for doc_type, required, desc in BASE_DOCUMENTS:
        checklist.append({
            "type": doc_type.value if isinstance(doc_type, DocumentType) else doc_type,
            "required": required,
            "description": desc,
            "category": "personal",
        })

    # Conditional: marital status
    if marital_status in ("married", "divorced"):
        for doc_type, required, desc in CONDITIONAL_DOCUMENTS.get(marital_status, []):
            checklist.append({
                "type": doc_type.value if isinstance(doc_type, DocumentType) else doc_type,
                "required": required,
                "description": desc,
                "category": "personal",
            })

    # Conditional: property
    if has_property_types:
        if "apartment" in has_property_types or "house" in has_property_types:
            for doc_type, required, desc in CONDITIONAL_DOCUMENTS["has_property_apartment"]:
                checklist.append({
                    "type": doc_type.value if isinstance(doc_type, DocumentType) else doc_type,
                    "required": required,
                    "description": desc,
                    "category": "property",
                })
        if "car" in has_property_types:
            for doc_type, required, desc in CONDITIONAL_DOCUMENTS["has_property_car"]:
                checklist.append({
                    "type": doc_type.value if isinstance(doc_type, DocumentType) else doc_type,
                    "required": required,
                    "description": desc,
                    "category": "property",
                })

    # Conditional: employment
    if is_employed is False:
        for doc_type, required, desc in CONDITIONAL_DOCUMENTS.get("unemployed", []):
            checklist.append({
                "type": doc_type if isinstance(doc_type, str) else doc_type.value,
                "required": required,
                "description": desc,
                "category": "employment",
            })

    # Credits
    if creditors_count > 0:
        for doc_type, required, desc in CONDITIONAL_DOCUMENTS.get("has_credits", []):
            checklist.append({
                "type": doc_type.value if isinstance(doc_type, DocumentType) else doc_type,
                "required": required,
                "description": desc,
                "category": "financial",
            })

    # Process documents
    for doc_type, required, desc in PROCESS_DOCUMENTS:
        checklist.append({
            "type": doc_type.value if isinstance(doc_type, DocumentType) else doc_type,
            "required": required,
            "description": desc,
            "category": "process",
        })

    return checklist


def calculate_completeness(checklist: list[dict], collected_types: set[str]) -> dict:
    """Calculate document collection progress.
    
    Returns: {total, collected, missing, required_missing, progress_percent}
    """
    required = [d for d in checklist if d["required"]]
    total = len(checklist)
    collected = sum(1 for d in checklist if d["type"] in collected_types)
    required_collected = sum(1 for d in required if d["type"] in collected_types)
    required_missing = [d for d in required if d["type"] not in collected_types]

    progress = round((required_collected / len(required) * 100) if required else 100, 1)

    return {
        "total": total,
        "collected": collected,
        "missing": len(required_missing),
        "required_missing": required_missing,
        "progress_percent": progress,
        "is_complete": len(required_missing) == 0,
    }
