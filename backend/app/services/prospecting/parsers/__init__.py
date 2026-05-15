"""Prospect parsers for automated sources."""

from .base import BaseParser, ParserConfig
from .efrsb import EFRSBParser
from .fns import FNSParser
from .fssp import FSSPParser
from .kad_arbitr import KADArbitrParser
from .mfc import MFCParser
from .rosreestr import RosreestrParser

__all__ = [
    "BaseParser",
    "ParserConfig",
    "FSSPParser",
    "EFRSBParser",
    "KADArbitrParser",
    "FNSParser",
    "RosreestrParser",
    "MFCParser",
]
