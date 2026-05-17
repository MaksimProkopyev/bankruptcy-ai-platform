from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ChannelEnum(str, Enum):
    WEB = "web"
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    VK = "vk"
    EMAIL = "email"
    OK = "ok"
    FACEBOOK = "facebook"
    AVITO = "avito"
    CALLBACK = "callback"
    MAX = "max"


@dataclass
class ContactInfo:
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    external_id: Optional[str] = None


@dataclass
class LeadEvent:
    channel: ChannelEnum
    external_id: str
    contact: ContactInfo
    message: str
    meta: dict = field(default_factory=dict)
    debt_amount: Optional[float] = None
    debt_type: Optional[str] = None


class ChannelAdapter(ABC):
    channel: ChannelEnum

    @abstractmethod
    async def normalize(self, raw_payload: dict) -> LeadEvent:
        """Нормализует сырой webhook payload в LeadEvent"""
        ...

    @abstractmethod
    async def send_message(self, lead_id: str, text: str) -> bool:
        """Отправляет исходящее сообщение в канал"""
        ...
