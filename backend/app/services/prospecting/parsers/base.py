"""Base parser for automated prospect sources."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

from app.schemas.prospect import RawProspect


@dataclass
class ParserConfig:
    """Конфигурация парсера."""
    mock_mode: bool = True
    regions: Optional[List[str]] = None
    min_debt: Optional[float] = None
    filter: Optional[str] = None


class BaseParser(ABC):
    """Базовый парсер для автоматических источников."""

    def __init__(self, config: dict):
        self.config = ParserConfig(**config)
        self.mock_mode = self.config.mock_mode

    @abstractmethod
    async def fetch(self) -> List[RawProspect]:
        """Получить сырые записи из источника."""
        pass

    @abstractmethod
    def get_source_type(self) -> str:
        """Вернуть source_type (например, 'fssp')."""
        pass

    def get_source_category(self) -> str:
        """Вернуть source_category (по умолчанию 'government')."""
        return "government"

    def get_acquisition_mode(self) -> str:
        """Режим получения данных."""
        return "parsed"