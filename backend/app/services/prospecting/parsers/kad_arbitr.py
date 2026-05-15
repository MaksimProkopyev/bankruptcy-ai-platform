"""KAD Arbitr parser for stalled bankruptcy cases."""

import random
from typing import List

from app.schemas.prospect import RawProspect

from .base import BaseParser


class KADArbitrParser(BaseParser):
    """Парсер КАД Арбитр — дела без движения/возвращённые."""

    def get_source_type(self) -> str:
        return "kad_arbitr"

    async def fetch(self) -> List[RawProspect]:
        if self.mock_mode:
            return self._mock_fetch()
        else:
            raise NotImplementedError("Real KAD Arbitr API not implemented yet")

    def _mock_fetch(self) -> List[RawProspect]:
        mock_names = [
            ("Морозов", "Андрей", "Викторович"),
            ("Зайцева", "Екатерина", "Алексеевна"),
            ("Волков", "Сергей", "Николаевич"),
            ("Романова", "Анастасия", "Дмитриевна"),
            ("Ковалёв", "Павел", "Игоревич"),
        ]

        prospects = []
        for i in range(random.randint(3, 7)):
            last, first, middle = random.choice(mock_names)
            full_name = f"{last} {first} {middle}"
            region = random.choice(["77", "50", "78"])
            case_num = f"А41-{random.randint(70000, 80000)}/2026"

            prospects.append(
                RawProspect(
                    source_category="government",
                    source_type="kad_arbitr",
                    acquisition_mode="parsed",
                    source_external_id=case_num,
                    source_url=f"https://kad.arbitr.ru/Card/{case_num}",
                    source_raw_data={
                        "case_number": case_num,
                        "court": "Арбитражный суд Московской области",
                        "status": "оставлено без движения",
                        "reason": "непредставление документов",
                        "last_action_date": "2026-01-20",
                    },
                    full_name=full_name,
                    inn=f"{region}{random.randint(1000000, 9999999)}",
                    phone=f"+7{random.randint(900, 999)}{random.randint(1000000, 9999999)}",
                    region=region,
                    debt_amount=random.randint(500000, 3000000),
                    debt_type="credit",
                    creditor_count=random.randint(1, 4),
                    has_property=random.choice([True, False, None]),
                )
            )

        return prospects
