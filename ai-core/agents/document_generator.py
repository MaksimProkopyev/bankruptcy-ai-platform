"""AI Agent: Document Generation.

Generates legal documents for bankruptcy cases:
- Bankruptcy application (заявление о банкротстве)
- Creditors registry (реестр кредиторов)
- Asset inventory (опись имущества)

Uses templates + AI to fill in case-specific details.
"""

import os
from datetime import datetime

import anthropic


APPLICATION_TEMPLATE = """ЗАЯВЛЕНИЕ
о признании гражданина несостоятельным (банкротом)

В Арбитражный суд {court_name}
Адрес суда: {court_address}

Заявитель (Должник):
{client_full_name}
Дата рождения: {birth_date}
Место рождения: {birth_place}
Адрес регистрации: {registration_address}
ИНН: {inn}
СНИЛС: {snils}
Телефон: {phone}

ЗАЯВЛЕНИЕ
о признании гражданина несостоятельным (банкротом)

Я, {client_full_name}, обращаюсь в Арбитражный суд с заявлением о признании 
меня несостоятельным (банкротом) на основании статей 213.3–213.5 Федерального 
закона от 26.10.2002 № 127-ФЗ «О несостоятельности (банкротстве)».

1. ОБСТОЯТЕЛЬСТВА ДЕЛА

Общая сумма моих обязательств перед кредиторами составляет {total_debt} руб.
Задолженность образовалась перед следующими кредиторами:

{creditors_list}

{additional_circumstances}

2. ИМУЩЕСТВЕННОЕ ПОЛОЖЕНИЕ

{property_description}

Ежемесячный доход составляет: {monthly_income} руб.
{employment_status}

3. СЕМЕЙНОЕ ПОЛОЖЕНИЕ

{family_status}

4. СДЕЛКИ ЗА ПОСЛЕДНИЕ 3 ГОДА

{transactions_3y}

5. ОБОСНОВАНИЕ

Размер моих обязательств составляет {total_debt} руб., что превышает 
500 000 руб. Удовлетворение требований одного или нескольких кредиторов 
приводит к невозможности исполнения обязательств перед другими кредиторами.

На основании изложенного, руководствуясь ст. 213.3–213.5 ФЗ «О несостоятельности 
(банкротстве)»,

ПРОШУ:

1. Признать меня, {client_full_name}, несостоятельным (банкротом).
2. Ввести процедуру {requested_procedure}.
3. Утвердить финансового управляющего из числа членов {sro_name}.

Приложения:
{attachments_list}

Дата: {filing_date}
Подпись: ___________________ / {client_full_name} /
"""


class DocumentGenerator:
    """Generate legal documents for bankruptcy cases."""

    def __init__(self, api_key: str | None = None):
        self.client = anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        )

    async def generate_application(
        self,
        case_data: dict,
        client_data: dict,
        creditors_data: list[dict],
    ) -> dict:
        """Generate bankruptcy application.
        
        Returns: {text, warnings, filled_fields, missing_fields}
        """
        # Build creditors list
        creditors_lines = []
        for i, cr in enumerate(creditors_data, 1):
            line = (
                f"{i}. {cr.get('name', 'Неизвестно')} "
                f"({cr.get('creditor_type', '')}) — "
                f"{cr.get('total_amount', 0):,.0f} руб."
            )
            if cr.get('contract_number'):
                line += f" (договор № {cr['contract_number']}"
                if cr.get('contract_date'):
                    line += f" от {cr['contract_date']}"
                line += ")"
            creditors_lines.append(line)

        # Determine court
        region = client_data.get("region", "")
        court_name = case_data.get("court_name", f"Арбитражный суд {region}")

        # Fill template
        fields = {
            "court_name": court_name,
            "court_address": "",  # TODO: lookup by court name
            "client_full_name": f"{client_data.get('last_name', '')} {client_data.get('first_name', '')} {client_data.get('patronymic', '')}".strip(),
            "birth_date": client_data.get("birth_date", "___________"),
            "birth_place": "___________",
            "registration_address": client_data.get("registration_address", "___________"),
            "inn": client_data.get("inn", "___________"),
            "snils": client_data.get("snils", "___________"),
            "phone": client_data.get("phone", "___________"),
            "total_debt": f"{case_data.get('total_debt', 0):,.0f}",
            "creditors_list": "\n".join(creditors_lines) if creditors_lines else "Информация о кредиторах прилагается отдельно.",
            "monthly_income": f"{client_data.get('monthly_income', 0):,.0f}" if client_data.get("monthly_income") else "отсутствует",
            "filing_date": datetime.now().strftime("%d.%m.%Y"),
            "sro_name": case_data.get("financial_manager_sro", "___________"),
        }

        # Use AI to fill in narrative sections
        narrative = await self._generate_narrative(case_data, client_data, creditors_data)
        fields.update(narrative)

        # Fill template
        try:
            text = APPLICATION_TEMPLATE.format(**fields)
        except KeyError as e:
            text = APPLICATION_TEMPLATE
            for key, value in fields.items():
                text = text.replace(f"{{{key}}}", str(value))

        # Check for missing fields
        missing = [f for f in ["inn", "snils", "registration_address"] if fields.get(f, "").startswith("___")]
        warnings = [f"Не заполнено поле: {f}" for f in missing]

        return {
            "text": text,
            "warnings": warnings,
            "filled_fields": len([v for v in fields.values() if v and not str(v).startswith("___")]),
            "total_fields": len(fields),
        }

    async def _generate_narrative(
        self, case_data: dict, client_data: dict, creditors_data: list[dict]
    ) -> dict:
        """Use LLM to generate narrative sections of the application."""
        prompt = f"""На основе данных клиента сгенерируй тексты для разделов заявления о банкротстве.
Отвечай ТОЛЬКО JSON:

Данные:
- Должник: {client_data.get('last_name', '')} {client_data.get('first_name', '')}
- Долг: {case_data.get('total_debt', 0)} руб.
- Кредиторы: {len(creditors_data)} шт.
- Доход: {client_data.get('monthly_income', 'нет')} руб./мес
- Работает: {'да' if client_data.get('is_employed') else 'нет'}
- Семейное положение: {client_data.get('marital_status', 'не указано')}

Верни JSON:
{{
    "additional_circumstances": "описание обстоятельств возникновения задолженности (2-3 предложения)",
    "property_description": "описание имущественного положения",
    "employment_status": "описание трудового статуса",
    "family_status": "описание семейного положения и наличия иждивенцев",
    "transactions_3y": "информация о сделках за 3 года (или 'Сделки с имуществом за последние 3 года не совершались.')",
    "requested_procedure": "реализации имущества" или "реструктуризации долгов",
    "attachments_list": "пронумерованный список приложений"
}}"""

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )

        try:
            import json
            raw = response.content[0].text
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(raw)
        except Exception:
            return {
                "additional_circumstances": "___________",
                "property_description": "___________",
                "employment_status": "___________",
                "family_status": "___________",
                "transactions_3y": "Сделки с имуществом за последние 3 года не совершались.",
                "requested_procedure": "реализации имущества",
                "attachments_list": "1. Копия паспорта\n2. Копия СНИЛС\n3. Копия ИНН\n4. Справки о доходах\n5. Кредитный отчёт\n6. Реестр кредиторов\n7. Опись имущества\n8. Квитанция об оплате госпошлины (300 руб.)\n9. Квитанция о внесении депозита на вознаграждение ФУ (25 000 руб.)",
            }
