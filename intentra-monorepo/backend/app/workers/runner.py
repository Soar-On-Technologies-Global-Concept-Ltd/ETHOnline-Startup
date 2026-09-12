"""Starts the worker loops on the leader instance and stops them cleanly."""
import asyncio
import logging

from app.core.logging import log
from app.workers import blockchain, evidence, reconciliation
from app.workers.leader import Leadership

logger = logging.getLogger("workers")
CAMPAIGN_SECONDS = 10.0

_stop = asyncio.Event()
_leadership = Leadership()
_tasks: list[asyncio.Task] = []
_campaign: asyncio.Task | None = None


def is_leader() -> bool:
    return _leadership.held


async def _start_loops() -> None:
    _tasks.extend([asyncio.create_task(blockchain.run_watcher(_stop), name="watcher"),
                   asyncio.create_task(blockchain.run_outbox(_stop), name="outbox"),
                   asyncio.create_task(reconciliation.run(_stop), name="reconciliation"),
                   asyncio.create_task(evidence.run(_stop), name="anchors")])
    log(logger, "workers started", loops=[t.get_name() for t in _tasks])


async def _campaign_loop() -> None:
    """Keep trying for leadership: whoever holds it may be a deploy that is going away."""
    while not _stop.is_set():
        try:
            if await _leadership.acquire():
                await _start_loops()
                return
        except Exception as err:
            log(logger, "leader election failed", error=f"{type(err).__name__}: {err}")
        try:
            await asyncio.wait_for(_stop.wait(), timeout=CAMPAIGN_SECONDS)
        except TimeoutError:
            pass


async def start() -> None:
    global _campaign
    _stop.clear()
    _campaign = asyncio.create_task(_campaign_loop(), name="leader-campaign")


async def stop() -> None:
    _stop.set()
    if _campaign is not None:
        await asyncio.gather(_campaign, return_exceptions=True)
    if _tasks:
        await asyncio.gather(*_tasks, return_exceptions=True)
        _tasks.clear()
    await _leadership.release()
