"""MFC parser for rejected extrajudicial bankruptcy applications."""

import random
from typing import List

from app.schemas.prospect import RawProspect
from .base import BaseParser


class MFCParser(BaseParser):
    """Парсер МФЦ — отказы во внесудебном банкротстве."""

    def get_source_type(self) -> str:
        return "mfc"

    async def fetch(self) -> List[RawProspect]:
        if self.mock_mode:
            return self._mock_fetch()
        else:
            raise NotImplementedError("Real MFC API not implemented yet")

    def _mock_fetch(self) -> List[RawProspect]:
        mock_names = [
            ("Гусев", "Евгений", "Михайлович"),
            ("Медведева", "Алина", "Валерьевна"),
            ("Ершов", "Денис", "Андреевич"),
            ("Сорокина", "Валентина", "Николаевна"),
            ("Крылов", "Станислав", "Олегович"),
        ]

        prospects = []
        for i in range(random.randint(3, 6)):
            last, first, middle = random.choice(mock_names)
            full_name = f"{last} {first} {middle}"
            region = random.choice(["77", "50", "78"])
            application_num = f"МФЦ-{region}-{random.randint(10000, 99999)}"

            prospects.append(
                RawProspect(
                    source_category="government",
                    source_type="mfc",
                    acquisition_mode="parsed",
                    source_external_id=application_num,
                    source_url=f"https://mfc.ru/applications/{application_num}",
                    source_raw_data={
                        "application_number": application_num,
                        "mfc_branch": f"МФЦ {region}",
                        "rejection_reason": "долг превышает 1 000 000 ₽",
                        "submission_date": "2026-03-01",
                        "rejection_date": "2026-03-15",
                    },
                    full_name=full_name,
                    inn=f"{region}{random.randint(1000000, 9999999)}",
                    phone=f"+7{random.randint(900, 999)}{random.randint(1000000, 9999999)}",
                    region=region,
                    debt_amount=random.randint(1200000, 5000000),
                    debt_type="mixed",
                    creditor_count=random.randint(2, 6),
                    has_property=random.choice([True, False]),
                )
            )

        return prospects