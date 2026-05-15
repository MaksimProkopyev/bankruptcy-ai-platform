"""Document service — template filling, PDF gen, versioning.

Flow: template + case data → AI fills variables → HTML → PDF/DOCX
"""

import hashlib
import re
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.billing_models import DocumentDraft, DocumentTemplate
from app.models.models import Case, Client

# ─── Variable resolver ───────────────────────────────────────


def _resolve_variables(case: Case, client: Client, creditors: list) -> dict:
    """Build a dict of all available template variables from case data."""
    full_name = f"{client.last_name or ''} {client.first_name or ''} {client.patronymic or ''}".strip()

    creditors_text = (
        "\n".join(
            [
                f"{i + 1}. {c.name} ({c.creditor_type}) — {c.total_amount:,.0f} руб."
                + (f" (договор № {c.contract_number})" if c.contract_number else "")
                for i, c in enumerate(creditors)
            ]
        )
        or "Информация о кредиторах прилагается отдельно."
    )

    total_debt = sum(c.total_amount for c in creditors) if creditors else (case.total_debt or 0)

    return {
        # Client
        "client_full_name": full_name,
        "client_last_name": client.last_name or "",
        "client_first_name": client.first_name or "",
        "client_patronymic": client.patronymic or "",
        "client_phone": client.phone or "",
        "client_email": client.email or "",
        "client_inn": client.inn or "___________",
        "client_snils": client.snils or "___________",
        "client_birth_date": client.birth_date.strftime("%d.%m.%Y") if client.birth_date else "___________",
        "client_registration_address": getattr(client, "registration_address", "___________") or "___________",
        # Case
        "case_number": case.case_number or "",
        "court_case_number": case.court_case_number or "",
        "total_debt": f"{total_debt:,.0f}",
        "total_debt_words": _num_to_words(float(total_debt)),
        "creditors_count": str(len(creditors)),
        "creditors_list": creditors_text,
        "court_name": case.court_name or "___________",
        "financial_manager": case.financial_manager_name or "___________",
        "financial_manager_sro": case.financial_manager_sro or "___________",
        # Fees
        "service_fee": f"{case.service_fee:,.0f}" if case.service_fee else "___________",
        "service_fee_words": _num_to_words(float(case.service_fee or 0)),
        # Dates
        "today_date": datetime.now().strftime("%d.%m.%Y"),
        "contract_date": datetime.now().strftime("%d.%m.%Y"),
        "filing_date": case.filing_date.strftime("%d.%m.%Y") if case.filing_date else "___________",
        # Company
        "company_name": 'ООО "Банкротство.AI"',
        "company_inn": "7700000000",
        "company_address": "г. Москва, ул. Примерная, д. 1",
        "company_phone": "8 800 123-45-67",
        "company_email": "info@bankruptcy.ai",
    }


def _num_to_words(n: float) -> str:
    """Simplified number to Russian words (for legal docs)."""
    n = int(n)
    if n == 0:
        return "ноль рублей"
    parts = []
    if n >= 1_000_000:
        m = n // 1_000_000
        parts.append(f"{m} млн")
        n %= 1_000_000
    if n >= 1_000:
        t = n // 1_000
        parts.append(f"{t} тыс.")
        n %= 1_000
    if n > 0:
        parts.append(str(n))
    return " ".join(parts) + " рублей"


# ─── Template filling ────────────────────────────────────────


def fill_template(template_html: str, variables: dict) -> str:
    """Replace {{variable}} placeholders with values."""

    def replacer(match):
        var_name = match.group(1).strip()
        return str(variables.get(var_name, f"[{var_name}]"))

    return re.sub(r"\{\{(\w+)\}\}", replacer, template_html)


def compute_hash(content: str) -> str:
    """SHA-256 hash of document content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


# ─── Service class ────────────────────────────────────────────


class DocumentService:
    """Generate and manage legal documents from templates."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_templates(self, category: str | None = None) -> list[DocumentTemplate]:
        query = select(DocumentTemplate).where(DocumentTemplate.is_active)
        if category:
            query = query.where(DocumentTemplate.category == category)
        result = await self.db.execute(query.order_by(DocumentTemplate.name))
        return list(result.scalars().all())

    async def generate_draft(
        self,
        template_id: UUID,
        case_id: UUID,
        created_by: UUID | None = None,
    ) -> DocumentDraft:
        """Generate a document draft from template + case data."""
        # Load template
        template = await self.db.get(DocumentTemplate, template_id)
        if not template:
            raise ValueError("Template not found")

        # Load case with relations
        case = await self.db.execute(select(Case).options(selectinload(Case.creditors)).where(Case.id == case_id))
        case = case.scalar_one_or_none()
        if not case:
            raise ValueError("Case not found")

        client = await self.db.get(Client, case.client_id)
        if not client:
            raise ValueError("Client not found")

        # Resolve variables
        variables = _resolve_variables(case, client, list(case.creditors))

        # Fill template
        filled_html = fill_template(template.content_html, variables)
        content_hash = compute_hash(filled_html)

        # Check for existing draft (versioning)
        existing = await self.db.execute(
            select(DocumentDraft)
            .where(DocumentDraft.case_id == case_id, DocumentDraft.template_id == template_id)
            .order_by(DocumentDraft.version.desc())
        )
        latest = existing.scalar_one_or_none()
        new_version = (latest.version + 1) if latest else 1

        # Create draft
        draft = DocumentDraft(
            case_id=case_id,
            template_id=template_id,
            title=f"{template.name} (v{new_version})",
            content_html=filled_html,
            filled_variables=variables,
            file_hash=content_hash,
            status="draft",
            version=new_version,
            parent_draft_id=latest.id if latest else None,
            created_by=created_by,
            requires_client_signature=template.category in ("contract", "act", "consent"),
            requires_lawyer_signature=template.category in ("application", "petition"),
        )
        self.db.add(draft)
        await self.db.flush()
        return draft

    async def approve_draft(self, draft_id: UUID, reviewer_id: UUID, notes: str | None = None) -> DocumentDraft:
        """Lawyer approves a draft."""
        draft = await self.db.get(DocumentDraft, draft_id)
        if not draft:
            raise ValueError("Draft not found")
        if draft.status not in ("draft", "review"):
            raise ValueError(f"Cannot approve draft in status: {draft.status}")

        draft.status = "approved"
        draft.reviewed_by = reviewer_id
        draft.reviewed_at = datetime.now()
        draft.review_notes = notes
        return draft

    async def send_for_signing(self, draft_id: UUID) -> DocumentDraft:
        """Mark draft as sent to client for signing."""
        draft = await self.db.get(DocumentDraft, draft_id)
        if not draft or draft.status != "approved":
            raise ValueError("Draft must be approved before signing")
        draft.status = "sent_for_signing"
        return draft


# ─── Seed templates ──────────────────────────────────────────

SEED_TEMPLATES = [
    {
        "name": "Договор на оказание юридических услуг",
        "slug": "service_contract",
        "category": "contract",
        "description": "Основной договор между компанией и клиентом на услуги по банкротству",
        "content_html": """<h1>ДОГОВОР № {{case_number}}</h1>
<p>на оказание юридических услуг по сопровождению процедуры банкротства</p>
<p>г. Москва &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {{contract_date}}</p>

<p>{{company_name}}, ИНН {{company_inn}}, в лице директора, действующего на основании Устава,
именуемое в дальнейшем «Исполнитель», с одной стороны, и</p>

<p>{{client_full_name}}, ИНН {{client_inn}}, СНИЛС {{client_snils}},
проживающий по адресу: {{client_registration_address}},
именуемый в дальнейшем «Заказчик», с другой стороны,</p>

<p>заключили настоящий Договор о нижеследующем:</p>

<h2>1. ПРЕДМЕТ ДОГОВОРА</h2>
<p>1.1. Исполнитель обязуется оказать Заказчику юридические услуги по сопровождению процедуры
банкротства физического лица в соответствии с ФЗ-127 «О несостоятельности (банкротстве)».</p>
<p>1.2. Общая сумма задолженности Заказчика перед кредиторами составляет {{total_debt}}
({{total_debt_words}}) перед {{creditors_count}} кредиторами.</p>

<h2>2. СТОИМОСТЬ УСЛУГ</h2>
<p>2.1. Стоимость услуг Исполнителя составляет {{service_fee}} ({{service_fee_words}}).</p>
<p>2.2. Оплата производится в соответствии с графиком, приведённым в Приложении №1.</p>

<h2>3. ОБЯЗАННОСТИ СТОРОН</h2>
<p>3.1. Исполнитель обязуется: подготовить и подать заявление о банкротстве, представлять интересы
Заказчика в суде, обеспечить взаимодействие с финансовым управляющим, контролировать сроки.</p>
<p>3.2. Заказчик обязуется: предоставить достоверные документы, своевременно оплачивать услуги,
не совершать сделки с имуществом без согласования с Исполнителем.</p>

<h2>4. ЭЛЕКТРОННАЯ ПОДПИСЬ</h2>
<p>4.1. Стороны договорились, что подписание настоящего Договора посредством ввода SMS-кода,
направленного на номер {{client_phone}}, является аналогом собственноручной подписи Заказчика
в соответствии со ст. 6 ФЗ-63 «Об электронной подписи».</p>

<p style="margin-top:40px">Исполнитель: {{company_name}}<br/>
Заказчик: {{client_full_name}}</p>""",
        "variables": [
            {"name": "case_number", "source": "case.case_number", "required": True},
            {"name": "client_full_name", "source": "client.full_name", "required": True},
            {"name": "client_inn", "source": "client.inn", "required": False},
            {"name": "client_snils", "source": "client.snils", "required": False},
            {"name": "client_phone", "source": "client.phone", "required": True},
            {"name": "total_debt", "source": "case.total_debt", "required": True},
            {"name": "service_fee", "source": "case.service_fee", "required": True},
        ],
    },
    {
        "name": "Доверенность на представление интересов",
        "slug": "power_of_attorney",
        "category": "power_of_attorney",
        "description": "Доверенность на представление интересов в арбитражном суде",
        "content_html": """<h1>ДОВЕРЕННОСТЬ</h1>
<p>г. Москва &nbsp;&nbsp;&nbsp;&nbsp; {{today_date}}</p>
<p>Я, {{client_full_name}}, {{client_birth_date}} года рождения, ИНН {{client_inn}},
СНИЛС {{client_snils}}, проживающий по адресу: {{client_registration_address}},</p>
<p>настоящей доверенностью уполномочиваю {{company_name}} представлять мои интересы
в Арбитражном суде по делу о банкротстве, с правом подачи заявлений, ходатайств,
получения документов и совершения иных процессуальных действий.</p>
<p>Доверенность выдана сроком на один год без права передоверия.</p>
<p style="margin-top:40px">Доверитель: {{client_full_name}}<br/>Подпись: ___________________</p>""",
        "variables": [
            {"name": "client_full_name", "source": "client.full_name", "required": True},
        ],
    },
    {
        "name": "Акт выполненных работ",
        "slug": "completion_act",
        "category": "act",
        "description": "Акт приёмки оказанных юридических услуг",
        "content_html": """<h1>АКТ № ____ выполненных работ</h1>
<p>к Договору № {{case_number}} от {{contract_date}}</p>
<p>г. Москва &nbsp;&nbsp;&nbsp;&nbsp; {{today_date}}</p>
<p>{{company_name}} (Исполнитель) и {{client_full_name}} (Заказчик) составили настоящий Акт
о том, что Исполнитель оказал, а Заказчик принял следующие услуги:</p>
<table border="1" cellpadding="8" style="border-collapse:collapse;width:100%">
<tr><th>Услуга</th><th>Стоимость</th></tr>
<tr><td>Юридическое сопровождение процедуры банкротства</td><td>{{service_fee}} руб.</td></tr>
</table>
<p>Общая стоимость оказанных услуг: {{service_fee}} ({{service_fee_words}}).</p>
<p>Заказчик претензий по объёму, качеству и срокам оказания услуг не имеет.</p>
<p style="margin-top:40px">Исполнитель: {{company_name}}<br/>Заказчик: {{client_full_name}}</p>""",
        "variables": [
            {"name": "case_number", "source": "case.case_number", "required": True},
            {"name": "client_full_name", "source": "client.full_name", "required": True},
            {"name": "service_fee", "source": "case.service_fee", "required": True},
        ],
    },
    {
        "name": "Согласие на обработку персональных данных",
        "slug": "pd_consent",
        "category": "consent",
        "description": "Согласие на обработку ПД (152-ФЗ)",
        "content_html": """<h1>СОГЛАСИЕ на обработку персональных данных</h1>
<p>Я, {{client_full_name}}, даю своё согласие {{company_name}} на обработку моих персональных
данных в целях оказания юридических услуг по сопровождению процедуры банкротства.</p>
<p>Перечень данных: ФИО, дата рождения, паспортные данные, ИНН, СНИЛС, контактная информация,
сведения о доходах, имуществе, обязательствах и кредитной истории.</p>
<p>Согласие даётся на срок действия договора и 5 лет после его прекращения.</p>
<p>Дата: {{today_date}}<br/>{{client_full_name}}</p>""",
        "variables": [
            {"name": "client_full_name", "source": "client.full_name", "required": True},
        ],
    },
]
