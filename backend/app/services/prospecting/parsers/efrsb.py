"""EFRSB parser for bankruptcy cases without representative."""

import random
from typing import List

from app.schemas.prospect import RawProspect
from .base import BaseParser


class EFRSBParser(BaseParser):
    """Парсер ЕФРСБ — банкротные дела без представителя."""

    def get_source_type(self) -> str:
        return "efrsb"

    async def fetch(self) -> List[RawProspect]:
        if self.mock_mode:
            return self._mock_fetch()
        else:
            raise NotImplementedError("Real EFRSB API not implemented yet")

    def _mock_fetch(self) -> List[RawProspect]:
        mock_names = [
            ("Козлов", "Артём", "Владимирович"),
            ("Орлова", "Светлана", "Петровна"),
            ("Лебедев", "Игорь", "Анатольевич"),
            ("Григорьева", "Татьяна", "Сергеевна"),
            ("Тихонов", "Михаил", "Игоревич"),
        ]

        prospects = []
        for i in range(random.randint(4, 8)):
            last, first, middle = random.choice(mock_names)
            full_name = f"{last} {first} {middle}"
            region = random.choice(["77", "50", "78"])
            case_num = f"А40-{random.randint(20000, 30000)}/2026"

            prospects.append(
                RawProspect(
                    source_category="government",
                    source_type="efrsb",
                    acquisition_mode="parsed",
                    source_external_id=case_num,
                    source_url=f"https://efrsb.ru/cases/{case_num}",
                    source_raw_data={
                        "case_number": case_num,
                        "court": "Арбитражный суд г. Москвы",
                        "status": "без представителя",
                        "debtor_type": "individual",
                        "publication_date": "2026-02-10",
                    },
                    full_name=full_name,
                    inn=f"{region}{random.randint(1000000, 9999999)}",
                    phone=f"+7{random.randint(900, 999)}{random.randint(1000000, 9999999)}",
                    region=region,
                    debt_amount=random.randint(300000, 2000000),
                    debt_type="mixed",
                    creditor_count=random.randint(2, 7),
                    has_property=random.choice([True, False]),
                )
            )

        return prospects