"""Outreach worker for leads from government data sources."""

import argparse
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.lead_models import Lead
from app.services.lead_collector.outreach import OutreachResult, OutreachSender
from config.collectors import GOV_SOURCES, OUTREACH_MAX_ATTEMPTS, OUTREACH_TEMPLATE, OUTREACH_WAIT_DAYS

logger = logging.getLogger("lead_outreach")


def _append_outreach_history(lead: Lead, result: OutreachResult) -> None:
    card = dict(lead.briefing_card or {})
    history = list(card.get("outreach_history") or [])
    history.append(
        {
            "at": datetime.now(timezone.utc).isoformat(),
            "channel": result.channel,
            "success": result.success,
            "provider_message_id": result.provider_message_id,
            "error": result.error,
            "attempt": (lead.contact_attempts or 0) + 1,
        }
    )
    card["outreach_history"] = history[-20:]
    lead.briefing_card = card


async def send_info_message(sender: OutreachSender, lead: Lead) -> OutreachResult:
    name = lead.name or "Здравствуйте"
    message = OUTREACH_TEMPLATE.format(name=name)
    return await sender.send(lead, message)


async def run_once() -> dict[str, int]:
    now = datetime.now(timezone.utc)
    wait_delta = timedelta(days=OUTREACH_WAIT_DAYS)
    processed = 0
    contacted = 0
    rejected = 0
    failed = 0
    sender = OutreachSender()

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Lead)
                .where(
                    Lead.source.in_(GOV_SOURCES),
                    Lead.deduplicated_from.is_(None),
                    Lead.status.in_(("new", "contacted")),
                    Lead.contact_attempts < OUTREACH_MAX_ATTEMPTS,
                )
                .order_by(Lead.created_at.asc())
                .limit(settings.LEAD_OUTREACH_BATCH_SIZE)
            )
            leads = result.scalars().all()

            for lead in leads:
                processed += 1
                if lead.contacted_at and (now - lead.contacted_at) < wait_delta:
                    continue
                result = await send_info_message(sender, lead)
                _append_outreach_history(lead, result)
                if result.channel != "none":
                    lead.contact_attempts = (lead.contact_attempts or 0) + 1
                if not result.success:
                    if result.channel == "none":
                        lead.status = "rejected"
                        rejected += 1
                    failed += 1
                    continue
                lead.status = "contacted"
                lead.contacted_at = now
                contacted += 1

            stale = await db.execute(
                select(Lead).where(
                    Lead.source.in_(GOV_SOURCES),
                    Lead.status == "contacted",
                    Lead.contact_attempts >= OUTREACH_MAX_ATTEMPTS,
                    Lead.contacted_at.is_not(None),
                    Lead.contacted_at < (now - wait_delta),
                )
            )
            for lead in stale.scalars().all():
                lead.status = "rejected"
                rejected += 1

            await db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.error("outreach_db_error error=%s", exc)
        return {
            "processed": 0,
            "contacted": 0,
            "failed": 0,
            "rejected": 0,
        }

    summary = {
        "processed": processed,
        "contacted": contacted,
        "failed": failed,
        "rejected": rejected,
    }
    logger.info(
        "outreach_run processed=%s contacted=%s failed=%s rejected=%s",
        summary["processed"],
        summary["contacted"],
        summary["failed"],
        summary["rejected"],
    )
    return summary


async def run_forever() -> None:
    while True:
        await run_once()
        await asyncio.sleep(6 * 60 * 60)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gov leads outreach worker")
    parser.add_argument("--once", action="store_true", help="Run one outreach cycle and exit")
    return parser.parse_args()


async def _main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    if args.once:
        await run_once()
        return
    await run_forever()


if __name__ == "__main__":
    asyncio.run(_main())
