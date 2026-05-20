"""Static configuration for the qualification agent."""

from __future__ import annotations

import os

# Retry windows (hours) per channel — index = retry attempt (0,1,2)
RETRY_CONFIG: dict[str, list[int]] = {
    "telegram": [1, 6, 24],
    "whatsapp": [2, 12, 48],
    "vk": [2, 12, 48],
    "email": [24, 72, 168],
    "callback": [0, 1, 6],  # callback — escalate almost immediately
    "ok": [4, 24, 72],
    "facebook": [2, 12, 48],
    "avito": [4, 24, 72],
    "web": [2, 12, 48],
    "max": [2, 12, 48],
}

# Score thresholds — see route_verdict in edges.py
SCORE_THRESHOLDS: dict[str, int] = {
    "auto_qualify": 71,  # score > 70 → create_prospect
    "auto_disqualify": 35,  # score < 36 → disqualify
    # 36..70 → soft_escalate (manager decides)
}

# Default question order for first-touch qualification
QUESTIONS_QUEUE_DEFAULT: list[str] = [
    "debt_amount",
    "debt_type",
    "has_property",
    "has_income",
    "region",
]

# Service URLs (overridable via env)
BACKEND_URL: str = os.getenv("BACKEND_URL", "http://backend:8000")
LEADGEN_URL: str = os.getenv("LEADGEN_URL", "http://leadgen:8002")
INTERNAL_SECRET: str = os.getenv("INTERNAL_SECRET", "")
