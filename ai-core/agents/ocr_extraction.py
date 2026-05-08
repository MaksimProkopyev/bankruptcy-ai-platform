"""AI Agent: Document OCR & Extraction.

Classifies document type and extracts structured data.
Pipeline: image/PDF → OCR text → LLM classification → LLM extraction.
"""

import os
import json
from dataclasses import dataclass

import anthropic


CLASSIFICATION_PROMPT = """Определи тип документа по его содержимому. 
Верни ТОЛЬКО JSON (без markdown):
{
    "document_type": "passport" | "snils" | "inn_cert" | "income_2ndfl" | 
                     "bank_statement" | "credit_report" | "credit_contract" |
                     "egrn_extract" | "vehicle_title" | "court_decision" | "other",
    "confidence": float (0-1),
    "reasoning": "краткое пояснение"
}"""


EXTRACTION_PROMPTS = {
    "passport": """Извлеки данные из паспорта РФ. Верни JSON:
{
    "full_name": "ФИО",
    "series": "серия (4 цифры)",
    "number": "номер (6 цифр)",
    "issued_by": "кем выдан",
    "issued_date": "дата выдачи (YYYY-MM-DD)",
    "department_code": "код подразделения",
    "birth_date": "дата рождения (YYYY-MM-DD)",
    "birth_place": "место рождения",
    "registration_address": "адрес регистрации"
}""",

    "income_2ndfl": """Извлеки данные из справки 2-НДФЛ. Верни JSON:
{
    "employee_name": "ФИО сотрудника",
    "employee_inn": "ИНН сотрудника",
    "employer_name": "наименование работодателя",
    "employer_inn": "ИНН работодателя",
    "year": число,
    "total_income": число (общая сумма дохода),
    "total_tax": число (общая сумма налога),
    "monthly_income": [{"month": 1, "amount": число}, ...]
}""",

    "credit_contract": """Извлеки данные из кредитного договора. Верни JSON:
{
    "creditor_name": "наименование кредитора",
    "contract_number": "номер договора",
    "contract_date": "дата договора (YYYY-MM-DD)",
    "loan_amount": число (сумма кредита),
    "interest_rate": число (процентная ставка),
    "monthly_payment": число (ежемесячный платёж),
    "loan_term_months": число (срок в месяцах),
    "is_secured": bool (есть ли залог),
    "security_type": "тип залога" | null
}""",

    "credit_report": """Извлеки данные из кредитного отчёта (БКИ). Верни JSON:
{
    "report_date": "дата отчёта",
    "total_active_loans": число,
    "total_debt": число (общая задолженность),
    "loans": [
        {
            "creditor": "название кредитора",
            "type": "credit" | "microloan" | "mortgage" | "card",
            "original_amount": число,
            "current_debt": число,
            "overdue_amount": число,
            "status": "active" | "closed" | "overdue"
        }
    ]
}""",

    "egrn_extract": """Извлеки данные из выписки ЕГРН. Верни JSON:
{
    "cadastral_number": "кадастровый номер",
    "address": "адрес объекта",
    "property_type": "квартира" | "дом" | "земельный участок" | "нежилое",
    "area_sqm": число (площадь в кв.м),
    "cadastral_value": число (кадастровая стоимость),
    "owner_name": "ФИО собственника",
    "ownership_date": "дата регистрации права",
    "encumbrances": ["описание обременений"] | []
}""",
}

DEFAULT_EXTRACTION = """Извлеки все ключевые данные из документа. Верни JSON с полями, 
которые удалось определить. Включи: даты, суммы, ФИО, номера документов, реквизиты."""


class OCRAgent:
    """Document classification and structured data extraction."""

    def __init__(self, api_key: str | None = None):
        self.client = anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        )
        self.model = "claude-sonnet-4-20250514"

    async def process_document(
        self,
        ocr_text: str,
        type_hint: str | None = None,
    ) -> dict:
        """Full pipeline: classify → extract → validate.
        
        Returns: {document_type, confidence, extracted_data, warnings}
        """
        # Step 1: Classify
        if type_hint and type_hint in EXTRACTION_PROMPTS:
            doc_type = type_hint
            classification_confidence = 0.9
        else:
            classification = await self._classify(ocr_text)
            doc_type = classification.get("document_type", "other")
            classification_confidence = classification.get("confidence", 0)

        # Step 2: Extract
        extraction_prompt = EXTRACTION_PROMPTS.get(doc_type, DEFAULT_EXTRACTION)
        extracted = await self._extract(ocr_text, extraction_prompt)

        # Step 3: Basic validation
        warnings = self._validate(doc_type, extracted)

        return {
            "document_type": doc_type,
            "confidence": classification_confidence,
            "extracted_data": extracted,
            "warnings": warnings,
        }

    async def _classify(self, text: str) -> dict:
        """Classify document type."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=500,
            system=CLASSIFICATION_PROMPT,
            messages=[{"role": "user", "content": f"Текст документа:\n\n{text[:3000]}"}],
        )
        try:
            return json.loads(response.content[0].text)
        except json.JSONDecodeError:
            return {"document_type": "other", "confidence": 0, "reasoning": "parse error"}

    async def _extract(self, text: str, prompt: str) -> dict:
        """Extract structured data using type-specific prompt."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            system=f"{prompt}\n\nОтвечай ТОЛЬКО JSON, без markdown.",
            messages=[{"role": "user", "content": f"Текст документа:\n\n{text[:8000]}"}],
        )
        try:
            raw = response.content[0].text
            # Strip potential markdown fencing
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"raw_text": text[:500], "parse_error": True}

    def _validate(self, doc_type: str, data: dict) -> list[str]:
        """Basic validation of extracted data."""
        warnings = []

        if data.get("parse_error"):
            warnings.append("Не удалось извлечь структурированные данные")
            return warnings

        if doc_type == "passport":
            if not data.get("full_name"):
                warnings.append("Не найдено ФИО")
            series = data.get("series", "")
            if series and (not series.isdigit() or len(series) != 4):
                warnings.append(f"Серия паспорта выглядит некорректно: {series}")

        elif doc_type == "credit_contract":
            if data.get("loan_amount", 0) <= 0:
                warnings.append("Не найдена сумма кредита")

        elif doc_type == "credit_report":
            loans = data.get("loans", [])
            if not loans:
                warnings.append("Не найдены записи о кредитах")

        return warnings
