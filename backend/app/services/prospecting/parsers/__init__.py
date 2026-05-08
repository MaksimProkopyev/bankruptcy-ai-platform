"""Prospect parsers for automated sources."""

from .base import BaseParser, ParserConfig
from .fssp import FSSPParser
from .efrsb import EFRSBParser
from .kad_arbitr import KADArbitrParser
from .fns import FNSParser
from .rosreestr import RosreestrParser
from .mfc import MFCParser

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