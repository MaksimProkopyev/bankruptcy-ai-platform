"""Leadgen service: calls the sales agent and sends the reply to the channel."""

from __future__ import annotations

import logging

logger = logging.getLogger("agent_trigger")


async def trigger_sales_agent(
    lead_id: str,
    message_text: str,
    channel: str,
    adapter,  # ChannelAdapter instance
) -> None:
    """Call the sales agent in the background and send reply to channel.

    Designed to run as a FastAPI BackgroundTask — must never raise so that
    the webhook handler always returns 200.
    """
    try:
        # Import lazily so leadgen can start without agents deps installed.
        # Module-level attribute is patched in tests via:
        #   patch("agents.sales.runner.process_message", ...)
        import agents.sales.runner as _sales_runner

        reply = await _sales_runner.process_message(
            lead_id=lead_id,
            message_text=message_text,
            channel=channel,
        )

        if reply:
            await adapter.send_message(lead_id=lead_id, text=reply)

    except Exception as exc:
        logger.error(
            "Sales agent error for lead %s: %s", lead_id, exc, exc_info=True
        )
