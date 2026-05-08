"""Rosreestr parser for property arrests and encumbrances."""

import random
from typing import List

from app.schemas.prospect import RawProspect
from .base import BaseParser


class RosreestrParser(BaseParser):
    """Парсер Росреестра — аресты и обременения имущества."""

    def get_source_type(self) -> str:
        return "rosreestr"

    async def fetch(self) -> List[RawProspect]:
        if self.mock_mode:
            return self._mock_fetch()
        else:
            raise NotImplementedError("Real Rosreestr API not implemented yet")

    def _mock_fetch(self) -> List[RawProspect]:
        mock_names = [
            ("Титов", "Геннадий", "Васильевич"),
            ("Белова", "Людмила", "Фёдоровна"),
            ("Комаров", "Виктор", "Петрович"),
            ("Ларина", "Надежда", "Анатольевна"),
            ("Шестаков", "Артур", "Романович"),
        ]

        prospects = []
        for i in range(random.randint(3, 6)):
            last, first, middle = random.choice(mock_names)
            full_name = f"{last} {first} {middle}"
            region = random.choice(["77", "50", "78"])
            cad_num = f"{region}:01:{random.randint(10000, 99999)}:{random.randint(1000, 9999)}"

            prospects.append(
                RawProspect(
                    source_category="government",
                    source_type="rosreestr",
                    acquisition_mode="parsed",
                    source_external_id=cad_num,
                    source_url=f"https://rosreestr.gov.ru/object/{cad_num}",
                    source_raw_data={
                        "cadastral_number": cad_num,
                        "property_type": random.choice(["apartment", "house", "land"]),
                        "encumbrance_type": "arrest",
                        "reason": "исполнительное производство",
                        "imposed_by": "ФССП",
                    },
                    full_name=full_name,
                    inn=f"{region}{random.randint(1000000, 9999999)}",
                    phone=f"+7{random.randint(900, 999)}{random.randint(1000000, 9999999)}",
                    region=region,
                    debt_amount=random.randint(800000, 5000000),
                    debt_type="credit",
                    creditor_count=random.randint(1, 3),
                    has_property=True,
                )
            )

        return prospects