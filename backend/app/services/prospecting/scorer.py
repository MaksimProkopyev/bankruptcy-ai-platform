"""Prospect scoring service."""

from app.schemas.prospect import RawProspect


class ProspectScorer:
    """Скоринг на основе доступных данных."""

    def score(self, prospect: RawProspect) -> tuple[int, str]:
        """Вернуть (score 0-100, temperature 'hot'|'warm'|'cold')."""
        score = 0

        # Сумма долга
        if prospect.debt_amount:
            if prospect.debt_amount >= 1_000_000:
                score += 30
            elif prospect.debt_amount >= 500_000:
                score += 20
            elif prospect.debt_amount >= 300_000:
                score += 10

        # Источник
        if prospect.source_category == "government":
            score += 15
        if prospect.source_type in ("fssp", "efrsb", "kad_arbitr"):
            score += 10  # горячие гос.

        # Контактные данные
        if prospect.phone:
            score += 15
        if prospect.email:
            score += 5

        # Регион
        if prospect.region in ("77", "50", "78"):
            score += 5

        # Несколько кредиторов
        if prospect.creditor_count and prospect.creditor_count >= 3:
            score += 10

        # Нет имущества (проще процедура)
        if prospect.has_property is False:
            score += 5

        # Реферал (высокая конверсия)
        if prospect.source_category == "referral":
            score += 20

        # Ограничить 0-100
        score = min(100, max(0, score))

        # Температура
        if score >= 60:
            temperature = "hot"
        elif score >= 30:
            temperature = "warm"
        else:
            temperature = "cold"

        return score, temperature