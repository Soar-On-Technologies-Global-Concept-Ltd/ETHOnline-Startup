"""Evidence anchors are best-effort: if one reverts or is dropped, queue it again once."""
import asyncio
import logging

from app.core.db import session_scope
from app.core.logging import log
from app.domains.evidence import service as evidence
from app.domains.payments import resolver
from app.domains.payments import service as payments
from app.domains.transactions import service as transactions

logger = logging.getLogger("worker.evidence")
RETRY_LIMIT = 2
INTERVAL = 30.0


async def retry_anchors() -> int:
    retried = 0
    async with session_scope() as s:
        for row in await evidence.unanchored(s):
            state = await payments.anchor_state(s, row.anchor_tx_id)
            if state not in ("FAILED", "STUCK"):
                continue
            if await payments.anchor_attempts(s, row.transaction_id, row.sha256) >= RETRY_LIMIT:
                continue
            tx = await transactions.get(s, row.transaction_id)
            queued = await resolver.queue_anchor(s, tx.id, tx.tx_key, row.sha256)
            await evidence.set_anchor_tx(s, row.id, queued.id)
            retried += 1
            log(logger, "anchor re-queued", evidence_id=str(row.id), chain_tx_id=queued.id)
    return retried


async def run(stop: asyncio.Event) -> None:
    while not stop.is_set():
        try:
            await retry_anchors()
        except Exception as err:
            log(logger, "anchor retry failed", error=f"{type(err).__name__}: {err}")
        try:
            await asyncio.wait_for(stop.wait(), timeout=INTERVAL)
        except TimeoutError:
            pass
