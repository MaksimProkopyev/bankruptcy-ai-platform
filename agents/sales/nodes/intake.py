"""Intake node — load lead from leadgen.leads and initialise state context."""

from __future__ import annotations

import os
from decimal import Decimal

import asyncpg

from ..state import SalesState


def _db_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    # asyncpg uses postgresql:// (not the SQLAlchemy postgresql+asyncpg:// scheme)
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    # Replace Docker-internal hostname for compatibility when running from the VM host
    url = url.replace("@postgres:", "@127.0.0.1:")
    return url


async def intake(state: SalesState) -> dict:
    """Load lead record from leadgen.leads and return a state patch.

    Raises:
        ValueError: If the lead_id is not found in the database.
    """
    lead_id = state["lead_id"]

    conn = await asyncpg.connect(_db_url())
    try:
        row = await conn.fetchrow(
            """
            SELECT debt_amount, debt_type, has_property, has_income, channel
            FROM   leadgen.leads
            WHERE  id = $1::uuid
            """,
            lead_id,
        )
    finally:
        await conn.close()

    if row is None:
        raise ValueError(f"Lead {lead_id!r} not found in leadgen.leads")

    debt_amount = row["debt_amount"]
    if isinstance(debt_amount, Decimal):
        debt_amount = float(debt_amount)

    return {
        "stage": "consult",
        "channel": row["channel"],
        "context": {
            "debt_amount":        debt_amount,
            "debt_type":          row["debt_type"],
            "has_property":       row["has_property"],
            "has_income":         row["has_income"],
            "objections_handled": [],
            "followup_count":     0,
        },
    }
