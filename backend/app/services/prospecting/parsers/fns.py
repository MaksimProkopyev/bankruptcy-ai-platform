"""FNS parser for former individual entrepreneurs with tax debt."""

import random
from typing import List

from app.schemas.prospect import RawProspect

from .base import BaseParser


class FNSParser(BaseParser):
    """Парсер ФНС — бывшие ИП с долгами."""

    def get_source_type(self) -> str:
        return "fns"

    async def fetch(self) -> List[RawProspect]:
        if self.mock_mode:
            return self._mock_fetch()
        else:
            raise NotImplementedError("Real FNS API not implemented yet")

    def _mock_fetch(self) -> List[RawProspect]:
        mock_names = [
            ("Семёнов", "Владимир", "Александрович"),
            ("Киселёва", "Оксана", "Витальевна"),
            ("Макаров", "Александр", "Сергеевич"),
            ("Филиппова", "Ирина", "Павловна"),
            ("Данилов", "Роман", "Иванович"),
        ]

        prospects = []
        for i in range(random.randint(4, 8)):
            last, first, middle = random.choice(mock_names)
            full_name = f"{last} {first} {middle}"
            region = random.choice(["77", "50", "78"])
            inn = f"{region}{random.randint(1000000, 9999999)}"

            prospects.append(
                RawProspect(
                    source_category="government",
                    source_type="fns",
                    acquisition_mode="parsed",
                    source_external_id=inn,
                    source_url=f"https://service.nalog.ru/inn/{inn}",
                    source_raw_data={
                        "inn": inn,
                        "status": "former_ip",
                        "tax_debt": True,
                        "debt_types": ["НДФЛ", "страховые взносы"],
                        "closure_date": "2025-08-01",
                    },
                    full_name=full_name,
                    inn=inn,
                    phone=f"+7{random.randint(900, 999)}{random.randint(1000000, 9999999)}",
                    region=region,
                    debt_amount=random.randint(200000, 1500000),
                    debt_type="tax",
                    creditor_count=1,
                    has_property=random.choice([True, False]),
                )
            )

        return prospects
