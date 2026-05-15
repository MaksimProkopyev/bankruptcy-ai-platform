"""FSSP parser for enforcement proceedings."""

import random
from typing import List

from app.schemas.prospect import RawProspect

from .base import BaseParser


class FSSPParser(BaseParser):
    """Парсер ФССП — исполнительные производства."""

    def get_source_type(self) -> str:
        return "fssp"

    async def fetch(self) -> List[RawProspect]:
        if self.mock_mode:
            return self._mock_fetch()
        else:
            # TODO: реализовать реальный запрос к API ФССП
            raise NotImplementedError("Real FSSP API not implemented yet")

    def _mock_fetch(self) -> List[RawProspect]:
        """Генерация реалистичных mock-данных."""
        regions = self.config.regions or ["77", "50", "78"]
        min_debt = self.config.min_debt or 500000

        mock_names = [
            ("Иванов", "Пётр", "Сергеевич"),
            ("Петрова", "Анна", "Ивановна"),
            ("Сидоров", "Константин", "Владимирович"),
            ("Кузнецова", "Елена", "Александровна"),
            ("Васильев", "Дмитрий", "Олегович"),
            ("Николаева", "Ольга", "Сергеевна"),
            ("Алексеев", "Алексей", "Алексеевич"),
            ("Смирнова", "Мария", "Дмитриевна"),
            ("Фёдоров", "Фёдор", "Фёдорович"),
            ("Павлова", "Юлия", "Викторовна"),
        ]

        prospects = []
        for i in range(random.randint(5, 10)):
            last, first, middle = random.choice(mock_names)
            full_name = f"{last} {first} {middle}"
            region = random.choice(regions)
            debt = random.randint(min_debt, min_debt * 3)
            external_id = f"{random.randint(10000, 99999)}/{random.randint(20, 25)}/{region}001-ИП"

            prospects.append(
                RawProspect(
                    source_category="government",
                    source_type="fssp",
                    acquisition_mode="parsed",
                    source_external_id=external_id,
                    source_url=f"https://fssp.gov.ru/production/{external_id}",
                    source_raw_data={
                        "production_number": external_id,
                        "debtor_type": "individual",
                        "initiator": random.choice(["Банк", "МФО", "ФНС", "УК"]),
                        "start_date": "2025-01-15",
                        "status": "active",
                    },
                    full_name=full_name,
                    inn=f"{region}{random.randint(1000000, 9999999)}",
                    phone=f"+7{random.randint(900, 999)}{random.randint(1000000, 9999999)}",
                    email=f"{first.lower()}.{last.lower()}@example.com",
                    region=region,
                    debt_amount=debt,
                    debt_type="credit",
                    creditor_count=random.randint(1, 5),
                    has_property=random.choice([True, False, None]),
                )
            )

        return prospects
