"""Two loops: the watcher reads escrow logs, the sender drains the outbox one transaction at a time."""
import asyncio
import logging

from app.core.config import get_settings
from app.core.logging import log
from app.domains.payments import outbox
from app.orchestration import chain_events

logger = logging.getLogger("worker.chain")


async def run_watcher(stop: asyncio.Event) -> None:
    await chain_events.run(stop)


async def run_outbox(stop: asyncio.Event) -> None:
    poll = get_settings().outbox_poll_seconds
    for raw in await outbox.recheck_sent():
        await chain_events.handle_raw_log(raw)
    while not stop.is_set():
        try:
            mined = await outbox.send_next()
            for raw in mined or []:
                await chain_events.handle_raw_log(raw)
        except Exception as err:
            mined = None
            log(logger, "outbox loop failed", error=f"{type(err).__name__}: {err}")
        if mined is not None:
            continue
        outbox.WAKE.clear()
        waiters = [asyncio.create_task(outbox.WAKE.wait()), asyncio.create_task(stop.wait())]
        done, pending = await asyncio.wait(waiters, timeout=poll, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
