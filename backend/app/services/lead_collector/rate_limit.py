"""Redis-backed throttling for external collector requests."""

from datetime import datetime, timezone
import asyncio
import logging
import math

import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger("lead_collector_rate_limit")


class CollectorRateLimiter:
    """Simple per-minute token limiter keyed by collector source."""

    def __init__(self) -> None:
        self.redis_client = redis.from_url(settings.REDIS_URL)

    async def wait_slot(self, source: str, requests_per_minute: int) -> None:
        if requests_per_minute <= 0:
            return

        try:
            now = datetime.now(timezone.utc)
            minute_bucket = now.strftime("%Y%m%d%H%M")
            key = f"lead_collector:throttle:{source}:{minute_bucket}"
            current = await self.redis_client.incr(key)
            if current == 1:
                await self.redis_client.expire(key, 90)
            if current <= requests_per_minute:
                return

            wait_seconds = max(1, 60 - now.second)
            wait_seconds = int(math.ceil(wait_seconds))
            logger.info(
                "throttle_wait source=%s rpm=%s current=%s wait_seconds=%s",
                source,
                requests_per_minute,
                current,
                wait_seconds,
            )
            await asyncio.sleep(wait_seconds)
        except Exception as exc:  # noqa: BLE001
            # Soft-fail: network glitches should not stop collection.
            logger.warning("throttle_skip source=%s reason=%s", source, exc)
