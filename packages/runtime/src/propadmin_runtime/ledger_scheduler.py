"""Local daily rent accrual equivalent to the authenticated cloud schedule."""

import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)
LONDON = ZoneInfo("Europe/London")


def london_day():
    return datetime.now(LONDON).date().isoformat()


async def start_local_ledger_scheduler(app, *, poll_seconds=60):
    """Accrue once before readiness, then on each new London day; caller cancels task."""
    day = london_day()
    await asyncio.to_thread(app.state.ledger.generate_rent_due, day)

    async def run():
        last_day = day
        while True:
            await asyncio.sleep(poll_seconds)
            current = london_day()
            if current == last_day:
                continue
            try:
                await asyncio.to_thread(app.state.ledger.generate_rent_due, current)
            except Exception:
                logger.exception("Local rent accrual failed for %s; retrying next minute", current)
            else:
                last_day = current

    return asyncio.create_task(run(), name="propadmin-local-rent-schedule")
