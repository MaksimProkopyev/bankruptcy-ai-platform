"""ORM models for leadgen/prospecting layer."""

import enum
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import (
    Column,
    String,
    Boolean,
    Integer,
    Text,
    DateTime,
    ForeignKey,
    Numeric,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.models import Base


# ---- Enums ----
class SourceCategory(str, enum.Enum):
    """Категория источника."""
    GOVERNMENT = "government"
    WEBSITE = "website"
    ADS = "ads"
    SOCIAL = "social"
    REFERRAL = "referral"
    PARTNER = "partner"
    MANUAL = "manual"


class AcquisitionMode(str, enum.Enum):
    """Режим получения данных."""
    PARSED = "parsed"
    INBOUND = "inbound"
    MANUAL = "manual"


class ProspectStatus(str, enum.Enum):
    """Статус prospect в воронке."""
    NEW = "new"
    ENRICHED = "enriched"
    CONTACTED = "contacted"
    CONVERTED = "converted"
    REJECTED = "rejected"
    STALE = "stale"


class Temperature(str, enum.Enum):
    """Температура prospect."""
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"


class DebtType(str, enum.Enum):
    """Тип долга."""
    CREDIT = "credit"
    TAX = "tax"
    ALIMONY = "alimony"
    UTILITY = "utility"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class OutreachChannel(str, enum.Enum):
    """Канал outreach."""
    SMS = "sms"
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    EMAIL = "email"
    PHONE = "phone"


# ---- Models ----
class Prospect(Base):
    """Prospect — потенциальный клиент до попадания в CRM."""

    __tablename__ = "prospects"
    __table_args__ = (
        UniqueConstraint("source_type", "source_external_id", name="uq_prospects_source_external_id"),
        Index("idx_prospects_status", "status"),
        Index("idx_prospects_category", "source_category"),
        Index("idx_prospects_source", "source_type"),
        Index("idx_prospects_inn", "inn"),
        Index("idx_prospects_phone", "phone"),
        Index("idx_prospects_region", "region"),
        Index("idx_prospects_temperature", "temperature"),
        Index("idx_prospects_created", "created_at"),
        Index("idx_prospects_score", "prospect_score"),
        Index("idx_prospects_utm", "utm_source", "utm_medium", "utm_campaign"),
        Index("idx_prospects_referral", "referral_code"),
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())

    # Источник (расширяемый)
    source_category = Column(String(20), nullable=False)
    source_type = Column(String(50), nullable=False)
    acquisition_mode = Column(String(10), nullable=False, server_default="inbound")
    source_external_id = Column(String(255), nullable=True)
    source_url = Column(Text, nullable=True)
    source_raw_data = Column(JSONB, nullable=True)

    # Персональные данные
    full_name = Column(String(255), nullable=True)
    inn = Column(String(12), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    region = Column(String(100), nullable=True)

    # Данные о долге (если известны)
    debt_amount = Column(Numeric(15, 2), nullable=True)
    debt_type = Column(String(50), nullable=True)
    creditor_count = Column(Integer, nullable=True)
    has_property = Column(Boolean, nullable=True)

    # Обогащение
    enrichment_data = Column(JSONB, nullable=True)
    enriched_at = Column(DateTime(timezone=True), nullable=True)

    # Статус-машина
    status = Column(String(20), nullable=False, server_default="new")

    # Outreach
    outreach_attempts = Column(Integer, nullable=False, server_default="0")
    last_outreach_at = Column(DateTime(timezone=True), nullable=True)
    outreach_channel = Column(String(20), nullable=True)
    outreach_response = Column(Text, nullable=True)

    # Конвертация в CRM
    converted_lead_id = Column(PGUUID(as_uuid=True), ForeignKey("leads.id"), nullable=True)
    converted_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(String(100), nullable=True)

    # Скоринг
    prospect_score = Column(Integer, nullable=False, server_default="0")
    temperature = Column(String(10), nullable=False, server_default="cold")

    # UTM-метки (для рекламных источников)
    utm_source = Column(String(100), nullable=True)
    utm_medium = Column(String(100), nullable=True)
    utm_campaign = Column(String(100), nullable=True)
    utm_content = Column(String(100), nullable=True)
    utm_term = Column(String(100), nullable=True)

    # Реферальные данные
    referral_code = Column(String(20), nullable=True)
    referrer_client_id = Column(PGUUID(as_uuid=True), ForeignKey("clients.id"), nullable=True)

    # Метаданные
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    converted_lead = relationship("Lead", foreign_keys=[converted_lead_id], uselist=False)
    referrer_client = relationship("Client", foreign_keys=[referrer_client_id], uselist=False)

    def __repr__(self) -> str:
        return f"<Prospect {self.id} {self.full_name} {self.source_type}>"


class ProspectSourceConfig(Base):
    """Конфигурация источников prospects."""

    __tablename__ = "prospect_sources_config"

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    source_category = Column(String(20), nullable=False)
    source_type = Column(String(50), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    display_icon = Column(String(10), nullable=True)
    acquisition_mode = Column(String(10), nullable=False, server_default="inbound")
    is_enabled = Column(Boolean, nullable=False, server_default="true")
    is_automated = Column(Boolean, nullable=False, server_default="false")
    schedule_cron = Column(String(50), nullable=True)
    config = Column(JSONB, nullable=False, server_default="{}")
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    last_run_status = Column(String(20), nullable=True)
    last_run_count = Column(Integer, nullable=False, server_default="0")
    stats = Column(JSONB, nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<ProspectSourceConfig {self.source_type} ({self.source_category})>"