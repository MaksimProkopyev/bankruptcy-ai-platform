"""Collector registry used by API and workers."""

from app.services.lead_collector.base import BaseCollector
from app.services.lead_collector.sources import (
    EFRSBCollector,
    FNSCollector,
    FSSPCollector,
    KadArbitrCollector,
    RosreestrCollector,
)

COLLECTOR_REGISTRY: dict[str, type[BaseCollector]] = {
    "fssp": FSSPCollector,
    "kad_arbitr": KadArbitrCollector,
    "efrsb": EFRSBCollector,
    "fns": FNSCollector,
    "rosreestr": RosreestrCollector,
}
