"""Lead source-specific collectors."""

from app.services.lead_collector.sources.efrsb import EFRSBCollector
from app.services.lead_collector.sources.fns import FNSCollector
from app.services.lead_collector.sources.fssp import FSSPCollector
from app.services.lead_collector.sources.kad_arbitr import KadArbitrCollector
from app.services.lead_collector.sources.rosreestr import RosreestrCollector

__all__ = [
    "EFRSBCollector",
    "FNSCollector",
    "FSSPCollector",
    "KadArbitrCollector",
    "RosreestrCollector",
]

