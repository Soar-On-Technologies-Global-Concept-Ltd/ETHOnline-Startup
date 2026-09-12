"""Deadlines fire without a human: auto-release, expiry, response and acceptance timeouts, stuck transactions (§9.3).

Everything here goes through the owning domain's service, so the loop never queries another domain's tables.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.core.config import get_settings
from app.core.db import session_scope, sessionmaker
from app.core.logging import log, transaction_id_var
from app.core.states import Event, TxState
from app.domains.authorization import service as authorization
from app.domains.disputes import service as disputes
from app.domains.payments import outbox, resolver
from app.domains.payments import service as payments
from app.domains.transactions import machine
from app.domains.transactions import service as transactions
from app.integrations.arc import client as arc_client
from app.orchestration import chain_events

logger = logging.getLogger("worker.reconcile")


async def _block_now() -> datetime | None:
    """Auto-release compares the chain's clock, not the server's."""
    try:
        block = await arc_client.w3().eth.get_block("latest")
        return datetime.fromtimestamp(int(block["timestamp"]), tz=timezone.utc)
    except Exception:
        return None


async def force_abandoned() -> int:
    """The escrow's own backstop: after fourteen days of silence anyone may close the intent, so we do it.

    There is no `release` on the canonical contract, so a delivered job that the customer never signs for is not
    released automatically — it waits for a signature or for this timeout. That is the contract's design.
    """
    now = await _block_now()
    if now is None:
        return 0
    cutoff = now - timedelta(days=14)
    async with sessionmaker()() as s:
        stale = await transactions.funded_since_before(s, cutoff)
    forced = 0
    for tx_id in stale:
        async with session_scope() as s:
            tx = await machine.lock(s, tx_id)
            transaction_id_var.set(str(tx.id))
            if tx.escrow_intent_id is None or tx.funded_at is None or tx.funded_at > cutoff:
                continue
            if await payments.has_execute_queued(s, tx.id):
                continue
            queued = await resolver.queue_abandonment(s, tx.id, tx.escrow_intent_id)
            await machine.note(s, tx, "system:reconciliation", "TX_QUEUED",
                               {"kind": "ABANDONMENT", "chain_tx_id": queued.id, "reason": "fourteen days of silence"})
            forced += 1
    return forced


async def expire_authorizations() -> int:
    states = [TxState.AWAITING_AUTHORIZATION.value, TxState.AUTHORIZED.value, TxState.FUNDING.value]
    async with sessionmaker()() as s:
        candidates = await transactions.in_states(s, states)
    cancelled = 0
    for tx_id in candidates:
        async with session_scope() as s:
            tx = await machine.lock(s, tx_id)
            if tx.state not in states:
                continue
            auth = await authorization.latest(s, tx.id)
            deadline = auth.expires_at if auth is not None else tx.expires_at
            if deadline is None or deadline > datetime.now(timezone.utc):
                continue
            if await payments.has_pending_funding(s, tx.id):
                continue                      # the money may already be in flight
            tx.close_reason = "authorization_expired"
            await machine.apply(s, tx, Event.AUTHORIZATION_EXPIRED, "system:reconciliation", {"expired_at": deadline})
            cancelled += 1
            log(logger, "authorization expired", transaction=str(tx.id))
    return cancelled


async def response_timeouts() -> int:
    async with sessionmaker()() as s:
        due = await disputes.due_responses(s)
    moved = 0
    for dispute_id, tx_id in due:
        async with session_scope() as s:
            tx = await machine.lock(s, tx_id)
            if tx.state != TxState.DISPUTED.value:
                continue
            await disputes.mark_no_response(s, dispute_id)
            await machine.apply(s, tx, Event.RESPONSE_TIMEOUT, "system:reconciliation", {"dispute_id": str(dispute_id)})
            moved += 1
        disputes.schedule_ladder(dispute_id)
    return moved


async def acceptance_timeouts() -> int:
    async with sessionmaker()() as s:
        due = await disputes.due_acceptances(s)
    escalated = 0
    for proposal_id, dispute_id, tx_id in due:
        async with session_scope() as s:
            tx = await machine.lock(s, tx_id)
            if tx.state != TxState.PROPOSED.value:
                continue
            await disputes.expire_proposal(s, proposal_id, dispute_id)
            await machine.apply(s, tx, Event.ACCEPT_TIMEOUT, "system:reconciliation", {"proposal_id": str(proposal_id)})
            escalated += 1
    return escalated


async def run_pending_ladders() -> int:
    async with sessionmaker()() as s:
        waiting = await disputes.awaiting_ladder(s)
    for dispute_id in waiting:
        disputes.schedule_ladder(dispute_id)
    return len(waiting)


async def close_late_disputes() -> int:
    async with sessionmaker()() as s:
        late = await disputes.opening_on_closed(s)
    closed = 0
    for dispute_id, tx_id in late:
        async with session_scope() as s:
            tx = await machine.lock(s, tx_id)
            await disputes.mark_too_late(s, tx.id)
            await machine.note(s, tx, "system:reconciliation", "DISPUTE_TOO_LATE", {"dispute_id": str(dispute_id)})
            closed += 1
    return closed


async def once() -> dict:
    counts = {"abandoned": await force_abandoned(), "expired": await expire_authorizations(),
              "response_timeouts": await response_timeouts(), "accept_timeouts": await acceptance_timeouts(),
              "ladders": await run_pending_ladders(), "late_disputes": await close_late_disputes()}
    for raw in await outbox.recheck_sent():
        await chain_events.handle_raw_log(raw)
    if any(counts.values()):
        log(logger, "reconciliation acted", **counts)
    return counts


async def run(stop: asyncio.Event) -> None:
    interval = get_settings().reconcile_interval_seconds
    while not stop.is_set():
        try:
            await once()
        except Exception as err:
            log(logger, "reconciliation failed", error=f"{type(err).__name__}: {err}")
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval)
        except TimeoutError:
            pass
