"""Worker entrypoint for government-source lead collection."""

import argparse
import asyncio
import logging
import time

from app.db.session import AsyncSessionLocal
from app.services.lead_collector.registry import COLLECTOR_REGISTRY

SCHEDULE_SECONDS: dict[str, int] = {
    "fssp": 24 * 60 * 60,
    "kad_arbitr": 12 * 60 * 60,
    "efrsb": 24 * 60 * 60,
    "fns": 7 * 24 * 60 * 60,
    "rosreestr": 7 * 24 * 60 * 60,
}

logger = logging.getLogger("lead_collectors")


async def run_once(source: str | None = None) -> None:
    sources = [source] if source else list(COLLECTOR_REGISTRY.keys())
    for source_name in sources:
        collector_cls = COLLECTOR_REGISTRY[source_name]
        async with AsyncSessionLocal() as db:
            summary = await collector_cls(db).collect()
        logger.info(
            "collector_run source=%s fetched=%s filtered=%s saved=%s duplicates=%s errors=%s duration_ms=%s",
            summary.source,
            summary.fetched,
            summary.filtered,
            summary.saved,
            summary.duplicates,
            len(summary.errors),
            summary.duration_ms,
        )
        if summary.errors:
            logger.warning("collector_errors source=%s errors=%s", summary.source, summary.errors)


async def run_forever() -> None:
    next_run_at = {source: 0.0 for source in COLLECTOR_REGISTRY}
    while True:
        now = time.time()
        for source, collector_cls in COLLECTOR_REGISTRY.items():
            if now < next_run_at[source]:
                continue
            async with AsyncSessionLocal() as db:
                summary = await collector_cls(db).collect()
            logger.info(
                "collector_run source=%s fetched=%s filtered=%s saved=%s duplicates=%s errors=%s duration_ms=%s",
                summary.source,
                summary.fetched,
                summary.filtered,
                summary.saved,
                summary.duplicates,
                len(summary.errors),
                summary.duration_ms,
            )
            if summary.errors:
                logger.warning("collector_errors source=%s errors=%s", summary.source, summary.errors)
            next_run_at[source] = now + SCHEDULE_SECONDS[source]
        await asyncio.sleep(30)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lead collectors worker")
    parser.add_argument("--once", action="store_true", help="Run one collection cycle and exit")
    parser.add_argument("--source", choices=sorted(COLLECTOR_REGISTRY.keys()), help="Run only one source")
    return parser.parse_args()


async def _main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    if args.once:
        await run_once(source=args.source)
        return
    if args.source:
        logger.warning("--source without --once is ignored in daemon mode")
    await run_forever()


if __name__ == "__main__":
    asyncio.run(_main())

