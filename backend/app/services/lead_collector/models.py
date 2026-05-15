"""Pydantic schemas for lead collector pipeline."""

from pydantic import BaseModel, Field


class RawLead(BaseModel):
    """Normalized lead payload from any external source."""

    external_id: str
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    region: str | None = None
    debt_amount_estimated: int | None = None  # kopecks
    source_url: str | None = None
    external_data: dict = Field(default_factory=dict)
    score: int | None = None


class CollectorRunSummary(BaseModel):
    """Collector run stats returned by worker and manual API run."""

    source: str
    fetched: int = 0
    filtered: int = 0
    saved: int = 0
    duplicates: int = 0
    errors: list[str] = Field(default_factory=list)
    duration_ms: int = 0
