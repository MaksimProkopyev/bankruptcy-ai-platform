"""AI Agent: Lead Qualification.

Determines if a person is eligible for bankruptcy,
recommends procedure type, estimates cost and timeline.
"""

import json
import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

import anthropic
from openai import OpenAI, APIError, APIConnectionError, RateLimitError

try:
    from gigachat import GigaChat
    from gigachat.exceptions import GigaChatException
    GIGACHAT_AVAILABLE = True
except ImportError:
    GIGACHAT_AVAILABLE = False
    GigaChat = None
    GigaChatException = Exception


SYSTEM_PROMPT = """Ты — AI-ассистент юридической компании по банкротству физических лиц.

Твоя задача — провести скоринг обращения и определить перспективы дела на основе предоставленных данных.

## Правила определения процедуры

### Судебное банкротство (реализация имущества)
- Долг от 500 000 ₽
- Нет стабильного дохода, достаточного для реструктуризации
- Есть признаки неплатёжеспособности

### Судебное банкротство (реструктуризация долгов)
- Долг от 500 000 ₽
- Есть стабильный доход
- Доход позволяет погасить долг за 3 года (с учётом прожиточного минимума)

### Внесудебное банкротство (через МФЦ)
- Долг от 25 000 до 1 000 000 ₽
- Окончено исполнительное производство по п.4 ч.1 ст.46 ФЗ-229
- Нет имущества и дохода для погашения

### Не подходит
- Долг менее 25 000 ₽
- Есть достаточный доход/имущество для погашения
- Иные основания

## Факторы риска (повышают сложность дела)
- Сделки с имуществом за последние 3 года (риск оспаривания)
- Сделки с родственниками
- Наличие залогового имущества
- Крупное имущество (недвижимость, авто)
- Наличие ИП или статуса учредителя
- Кредиты, взятые менее чем за год до обращения

## Расчёт стоимости
- Базовая стоимость услуг: 80 000 – 120 000 ₽
- Госпошлина: 300 ₽
- Депозит ФУ: 25 000 ₽
- Публикации ЕФРСБ: ~3 000 – 5 000 ₽
- Публикация Коммерсантъ: ~10 000 ₽
- Почтовые расходы: ~5 000 ₽

Стоимость увеличивается при:
- Количество кредиторов > 10: +10 000 ₽
- Наличие залогового имущества: +15 000 ₽
- Риск оспаривания сделок: +20 000 ₽
- Сложная кредитная история: +10 000 ₽

## Оценка сроков
- Подготовка и подача: 1-2 недели (с AI)
- Рассмотрение заявления: 1-3 месяца
- Реализация имущества: 6 месяцев (+ продления)
- Реструктуризация: до 3 лет
- Итого типовое дело: 8-12 месяцев

ОГРАНИЧЕНИЯ:
- НЕ давай юридических гарантий
- НЕ обещай конкретный результат
- При сложных ситуациях рекомендуй консультацию с юристом
- Всегда указывай уровень уверенности

Ответь ТОЛЬКО в формате JSON (без markdown):
{
    "is_eligible": bool,
    "recommended_procedure": "judicial" | "extrajudicial" | "not_eligible",
    "procedure_type": "asset_realization" | "restructuring" | null,
    "estimated_cost_min": number,
    "estimated_cost_max": number,
    "estimated_duration_months_min": number,
    "estimated_duration_months_max": number,
    "risk_level": "low" | "medium" | "high",
    "risk_factors": [string],
    "confidence": float (0-1),
    "explanation": string,
    "needs_lawyer_review": bool
}
"""


@dataclass
class QualificationInput:
    total_debt: float
    creditors_count: int
    creditor_types: list[str]
    monthly_income: float | None = None
    is_employed: bool = False
    has_property: bool = False
    property_types: list[str] | None = None
    has_transactions_3y: bool = False
    marital_status: str = "single"
    has_enforcement_proceedings: bool = False
    region: str | None = None


@dataclass
class QualificationResult:
    is_eligible: bool
    recommended_procedure: str
    procedure_type: str | None
    estimated_cost_min: float
    estimated_cost_max: float
    estimated_duration_months_min: int
    estimated_duration_months_max: int
    risk_level: str
    risk_factors: list[str]
    confidence: float
    explanation: str
    needs_lawyer_review: bool


@dataclass
class QualificationScore:
    """Числовой скор и маршрутизация лида."""
    score: int           # 0-100
    tier: str            # "hot" | "warm" | "cold" | "disqualified"
    sla_hours: int       # SLA первого контакта в часах
    briefing_card: dict  # Карточка для юриста


def calculate_score(result: QualificationResult, input_data: QualificationInput) -> QualificationScore:
    """
    Вычислить числовой скор и маршрутизацию.
    
    Логика скоринга (100 баллов):
    - is_eligible = False → score=0, tier=disqualified
    - Базовый балл: 40
    - Долг ≥ 500K → +15
    - Долг ≥ 1M → +5 доп.
    - confidence ≥ 0.8 → +10
    - risk_level = "low" → +15, "medium" → +5, "high" → -10
    - has_enforcement_proceedings = True → +10 (готов к делу)
    - has_property = False → +5 (чище процедура)
    - has_transactions_3y = True → -15
    - creditors_count > 10 → -5
    
    Тиры:
    - score ≥ 70 → Hot, SLA 1 час
    - score 40-69 → Warm, SLA 4 часа
    - score 20-39 → Cold, SLA 24 часа
    - score < 20 или disqualified → Disqualified
    
    briefing_card — dict с ключевой инфо для юриста:
    {
        "debt_summary": "общая сумма долга + кол-во кредиторов",
        "procedure": "рекомендуемая процедура",
        "risks": ["список рисков"],
        "urgency": "срочность",
        "recommended_action": "что сделать юристу",
        "score": число,
        "tier": тир,
    }
    """
    if not result.is_eligible:
        return QualificationScore(
            score=0, tier="disqualified", sla_hours=0,
            briefing_card={"recommended_action": "Отказ — клиент не соответствует критериям"}
        )
    
    score = 40
    if input_data.total_debt >= 500_000:
        score += 15
    if input_data.total_debt >= 1_000_000:
        score += 5
    if result.confidence >= 0.8:
        score += 10
    if result.risk_level == "low":
        score += 15
    elif result.risk_level == "medium":
        score += 5
    elif result.risk_level == "high":
        score -= 10
    if input_data.has_enforcement_proceedings:
        score += 10
    if not input_data.has_property:
        score += 5
    if input_data.has_transactions_3y:
        score -= 15
    if input_data.creditors_count > 10:
        score -= 5
    
    score = max(0, min(100, score))
    
    if score >= 70:
        tier, sla = "hot", 1
    elif score >= 40:
        tier, sla = "warm", 4
    elif score >= 20:
        tier, sla = "cold", 24
    else:
        tier, sla = "disqualified", 0
    
    briefing_card = {
        "debt_summary": f"{input_data.total_debt:,.0f} ₽, {input_data.creditors_count} кредиторов",
        "procedure": result.recommended_procedure,
        "procedure_type": result.procedure_type,
        "risks": result.risk_factors,
        "risk_level": result.risk_level,
        "urgency": "СРОЧНО" if tier == "hot" else ("Приоритет" if tier == "warm" else "Обычный"),
        "recommended_action": (
            "Позвонить в течение 1 часа" if tier == "hot" else
            "Позвонить в течение 4 часов" if tier == "warm" else
            "Обработать в течение 24 часов"
        ),
        "cost_estimate": f"{result.estimated_cost_min:,.0f}–{result.estimated_cost_max:,.0f} ₽",
        "duration_estimate": f"{result.estimated_duration_months_min}–{result.estimated_duration_months_max} мес.",
        "needs_lawyer_review": result.needs_lawyer_review,
        "score": score,
        "tier": tier,
    }
    
    return QualificationScore(score=score, tier=tier, sla_hours=sla, briefing_card=briefing_card)


logger = logging.getLogger(__name__)


class QualificationAgent:
    """Агент первичной квалификации — определяет перспективы банкротства.
    
    Поддерживает провайдеры: Anthropic (Claude), OpenAI (GPT-4), GigaChat, YandexGPT, Ollama.
    При ошибке одного провайдера автоматически переключается на другой.
    Если все недоступны, возвращает результат на основе rule-based pre-screening.
    """

    def __init__(
        self,
        anthropic_api_key: str | None = None,
        openai_api_key: str | None = None,
        gigachat_api_key: str | None = None,
        yandex_api_key: str | None = None,
        yandex_folder_id: str | None = None,
        ollama_base_url: str | None = None,
        anthropic_model: str = "claude-sonnet-4-20250514",
        openai_model: str = "gpt-4o",
        gigachat_model: str = "GigaChat",
        yandex_model: str = "yandexgpt",
        ollama_model: str = "llama3.2",
    ):
        self.anthropic_api_key = anthropic_api_key
        self.openai_api_key = openai_api_key
        self.gigachat_api_key = gigachat_api_key
        self.yandex_api_key = yandex_api_key
        self.yandex_folder_id = yandex_folder_id
        self.ollama_base_url = ollama_base_url
        self.anthropic_model = anthropic_model
        self.openai_model = openai_model
        self.gigachat_model = gigachat_model
        self.yandex_model = yandex_model
        self.ollama_model = ollama_model

        self.anthropic_client = None
        if anthropic_api_key:
            try:
                self.anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize Anthropic client: {e}")

        self.openai_client = None
        if openai_api_key:
            try:
                self.openai_client = OpenAI(api_key=openai_api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}")

        self.gigachat_client = None
        if gigachat_api_key and GIGACHAT_AVAILABLE:
            try:
                self.gigachat_client = GigaChat(
                    credentials=gigachat_api_key,
                    verify_ssl_certs=False,
                )
            except Exception as e:
                logger.warning(f"Failed to initialize GigaChat client: {e}")

        self.yandex_client = None
        if yandex_api_key and yandex_folder_id:
            try:
                self.yandex_client = OpenAI(
                    api_key=yandex_api_key,
                    base_url="https://llm.api.cloud.yandex.net/foundationModels/v1/",
                    default_headers={"x-folder-id": yandex_folder_id},
                )
            except Exception as e:
                logger.warning(f"Failed to initialize YandexGPT client: {e}")

        self.ollama_client = None
        if ollama_base_url:
            try:
                self.ollama_client = OpenAI(
                    api_key="ollama",  # dummy key
                    base_url=ollama_base_url,
                )
            except Exception as e:
                logger.warning(f"Failed to initialize Ollama client: {e}")

    async def qualify(self, input_data: QualificationInput) -> QualificationResult:
        """Run qualification scoring with fallback logic."""
        # Fast rule-based rejection before any LLM call.
        pre = pre_screen(input_data)
        if not pre.get("pass", True):
            return self._rule_based_fallback(input_data)

        user_message = self._build_user_message(input_data)

        # Try Anthropic first
        if self.anthropic_client:
            try:
                response = self.anthropic_client.messages.create(
                    model=self.anthropic_model,
                    max_tokens=2000,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": user_message}],
                )
                text = response.content[0].text
                data = json.loads(text)
                logger.info("Qualification completed via Anthropic")
                return self._parse_result(data)
            except (anthropic.APIError, anthropic.APIConnectionError, anthropic.RateLimitError) as e:
                logger.warning(f"Anthropic API error: {e}, falling back to OpenAI")
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Failed to parse Anthropic response: {e}")
                # Fall through
            except Exception as e:
                logger.warning(f"Anthropic unexpected error: {e}, falling back to OpenAI")

        # Try OpenAI
        if self.openai_client:
            try:
                response = self.openai_client.chat.completions.create(
                    model=self.openai_model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    max_tokens=2000,
                    response_format={"type": "json_object"},
                )
                text = response.choices[0].message.content
                data = json.loads(text)
                logger.info("Qualification completed via OpenAI")
                return self._parse_result(data)
            except (APIError, APIConnectionError, RateLimitError) as e:
                logger.warning(f"OpenAI API error: {e}")
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Failed to parse OpenAI response: {e}")

        # Try GigaChat
        if self.gigachat_client:
            try:
                response = self.gigachat_client.chat(
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    model=self.gigachat_model,
                    max_tokens=2000,
                )
                text = response.choices[0].message.content
                data = json.loads(text)
                logger.info("Qualification completed via GigaChat")
                return self._parse_result(data)
            except (GigaChatException, Exception) as e:
                logger.warning(f"GigaChat API error: {e}")

        # Try YandexGPT
        if self.yandex_client:
            try:
                response = self.yandex_client.chat.completions.create(
                    model=self.yandex_model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    max_tokens=2000,
                    response_format={"type": "json_object"},
                )
                text = response.choices[0].message.content
                data = json.loads(text)
                logger.info("Qualification completed via YandexGPT")
                return self._parse_result(data)
            except (APIError, APIConnectionError, RateLimitError) as e:
                logger.warning(f"YandexGPT API error: {e}")
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Failed to parse YandexGPT response: {e}")

        # Try Ollama
        if self.ollama_client:
            try:
                response = self.ollama_client.chat.completions.create(
                    model=self.ollama_model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    max_tokens=2000,
                    response_format={"type": "json_object"},
                )
                text = response.choices[0].message.content
                data = json.loads(text)
                logger.info("Qualification completed via Ollama")
                return self._parse_result(data)
            except (APIError, APIConnectionError, RateLimitError) as e:
                logger.warning(f"Ollama API error: {e}")
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Failed to parse Ollama response: {e}")

        # All providers failed, return rule-based fallback
        logger.warning("All LLM providers failed, returning rule-based fallback")
        return self._rule_based_fallback(input_data)

    def _parse_result(self, data: dict) -> QualificationResult:
        """Parse JSON response into QualificationResult."""
        return QualificationResult(
            is_eligible=data["is_eligible"],
            recommended_procedure=data["recommended_procedure"],
            procedure_type=data.get("procedure_type"),
            estimated_cost_min=data.get("estimated_cost_min", 0),
            estimated_cost_max=data.get("estimated_cost_max", 0),
            estimated_duration_months_min=data.get("estimated_duration_months_min", 0),
            estimated_duration_months_max=data.get("estimated_duration_months_max", 0),
            risk_level=data["risk_level"],
            risk_factors=data.get("risk_factors", []),
            confidence=data["confidence"],
            explanation=data["explanation"],
            needs_lawyer_review=data.get("needs_lawyer_review", False),
        )

    def _rule_based_fallback(self, input_data: QualificationInput) -> QualificationResult:
        """Generate a fallback result based on pre-screening rules."""
        pre = pre_screen(input_data)
        if not pre["pass"]:
            return QualificationResult(
                is_eligible=False,
                recommended_procedure="not_eligible",
                procedure_type=None,
                estimated_cost_min=0,
                estimated_cost_max=0,
                estimated_duration_months_min=0,
                estimated_duration_months_max=0,
                risk_level="low",
                risk_factors=[],
                confidence=0.7,
                explanation=pre["reason"] or "Не удалось подключиться к AI-моделям. На основе правил: " + pre.get("reason", "неизвестно"),
                needs_lawyer_review=True,
            )

        # If pre-screening passes, we still need some default values
        # This is a very basic fallback
        return QualificationResult(
            is_eligible=True,
            recommended_procedure="judicial",
            procedure_type="asset_realization",
            estimated_cost_min=80000,
            estimated_cost_max=150000,
            estimated_duration_months_min=8,
            estimated_duration_months_max=12,
            risk_level="medium",
            risk_factors=pre.get("flags", []),
            confidence=0.6,
            explanation="AI-модели временно недоступны. Предварительная оценка на основе правил: дело имеет перспективы, но требуется консультация юриста.",
            needs_lawyer_review=True,
        )

    def _build_user_message(self, data: QualificationInput) -> str:
        """Format input data into a clear message for the LLM."""
        def _fmt_amount(value: float) -> str:
            return f"{value:,.0f}".replace(",", " ")

        parts = [
            f"Общая сумма долга: {_fmt_amount(data.total_debt)} ₽",
            f"Количество кредиторов: {data.creditors_count}",
            f"Типы кредиторов: {', '.join(data.creditor_types)}",
        ]

        if data.monthly_income is not None:
            parts.append(f"Ежемесячный доход: {_fmt_amount(data.monthly_income)} ₽")
        
        parts.append(f"Трудоустроен: {'да' if data.is_employed else 'нет'}")
        parts.append(f"Наличие имущества: {'да' if data.has_property else 'нет'}")

        if data.property_types:
            parts.append(f"Типы имущества: {', '.join(data.property_types)}")
        
        parts.append(f"Сделки за 3 года: {'да' if data.has_transactions_3y else 'нет'}")
        parts.append(f"Семейное положение: {data.marital_status}")
        parts.append(
            f"Окончено исп. производство: {'да' if data.has_enforcement_proceedings else 'нет'}"
        )
        
        if data.region:
            parts.append(f"Регион: {data.region}")

        return "Данные клиента для квалификации:\n\n" + "\n".join(parts)


# ---- Rule-based pre-screening (fast, no LLM call) ----

def pre_screen(data: QualificationInput) -> dict:
    """Quick rule-based check before calling LLM.
    
    Returns basic eligibility and flags for AI to analyze deeper.
    """
    flags = []
    
    if data.total_debt < 25_000:
        return {
            "pass": False,
            "reason": "Сумма долга менее 25 000 ₽ — банкротство невозможно",
            "flags": [],
        }
    
    if data.has_transactions_3y:
        flags.append("risk:transactions_3y")
    
    if data.has_property and data.property_types:
        if "apartment" in data.property_types or "house" in data.property_types:
            flags.append("risk:real_estate")
        if "car" in data.property_types:
            flags.append("risk:vehicle")
    
    if data.creditors_count > 10:
        flags.append("complexity:many_creditors")
    
    if data.monthly_income and data.monthly_income > 0:
        # Rough check: can they pay off in 3 years?
        yearly_capacity = (data.monthly_income - 20_000) * 12  # minus living expenses
        if yearly_capacity * 3 >= data.total_debt:
            flags.append("option:restructuring")

    # Extrajudicial check
    is_extrajudicial_candidate = (
        25_000 <= data.total_debt <= 1_000_000
        and data.has_enforcement_proceedings
        and not data.has_property
    )
    if is_extrajudicial_candidate:
        flags.append("option:extrajudicial")
    
    return {"pass": True, "reason": None, "flags": flags}
