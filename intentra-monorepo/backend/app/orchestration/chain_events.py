"""The chain decides money states. Escrow logs are read here and turned into state, through each domain's service.

This is the only place FUNDED, DELIVERED, RELEASED, DISPUTED, SETTLED and refund-CANCELLED are applied, and every one
of them is checked field by field against what the backend actually requested (schematics §5.3, §9.1).
"""
import asyncio
import logging
from datetime import datetime, timezone

from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.columns import utcnow
from app.core.config import get_settings
from app.core.db import session_scope
from app.core.logging import log, transaction_id_var
from app.core.models import KvCursor
from app.core.states import Event
from app.domains.authorization import service as authorization
from app.domains.disputes import service as disputes
from app.domains.evidence import service as evidence
from app.domains.fulfillment import service as fulfillment
from app.domains.identity import service as identity
from app.domains.intents import service as intents
from app.domains.payments import service as payments
from app.domains.providers import service as providers
from app.domains.transactions import machine
from app.domains.transactions import service as transactions
from app.integrations.arc import client as arc_client
from app.integrations.arc.events import DecodedLog, decode

logger = logging.getLogger("chain")
CURSOR_KEY = "watcher_block"


def _hex_eq(a, b) -> bool:
    return a is not None and b is not None and str(a).lower() == str(b).lower()


def _at(seconds: int) -> datetime:
    return datetime.fromtimestamp(int(seconds), tz=timezone.utc)


async def _job_funded(s: AsyncSession, tx, ev: DecodedLog) -> str | None:
    auth = await authorization.latest(s, tx.id)
    if auth is None:
        return "funded without an authorization on file"
    a = ev.args
    checks = {
        "customer": _hex_eq(a["customer"], await identity.wallet_of(s, tx.customer_id)),
        "provider": _hex_eq(a["provider"], await providers.wallet_of(s, tx.provider_id)),
        "amount": int(a["amount"]) == int(tx.amount_minor or -1),
        "authorizationHash": _hex_eq(a["authorizationHash"], auth.authorization_hash),
        "disputeWindow": int(a["disputeWindow"]) == int(tx.dispute_window_s or -1),
        "expiresAt": tx.expires_at is not None and int(a["expiresAt"]) == int(tx.expires_at.timestamp()),
    }
    wrong = sorted(k for k, ok in checks.items() if not ok)
    if wrong:
        return f"JobFunded does not match the authorization: {', '.join(wrong)}"
    try:
        block = await arc_client.w3().eth.get_block(ev.block_number)
        when = _at(block["timestamp"])
    except Exception:
        when = utcnow()
    await transactions.mark_funded(s, tx, when)
    await payments.record(s, tx.id, "FUND", ev.tx_hash, int(a["amount"]))
    quote = await intents.quote_view(s, tx.quote_id)
    await fulfillment.ensure(s, tx.id, list((quote["scope"] if quote else {}).get("checklist", [])))
    await machine.apply(s, tx, Event.FUNDED_ONCHAIN, f"chain:{ev.tx_hash}",
                        {"amount_minor": int(a["amount"]), "tx_hash": ev.tx_hash, "block": ev.block_number})
    return None


async def _evidence_anchored(s: AsyncSession, tx, ev: DecodedLog) -> str | None:
    if not await evidence.mark_anchored(s, tx.id, str(ev.args["evidenceHash"]), ev.tx_hash):
        return "anchored a hash that is not evidence of this transaction"
    await machine.note(s, tx, f"chain:{ev.tx_hash}", "TX_MINED", {"kind": "ANCHOR", "tx_hash": ev.tx_hash})
    return None


async def _submitted(s: AsyncSession, tx, ev: DecodedLog) -> str | None:
    expected = await fulfillment.expected_deliverable(s, tx.id)
    if not _hex_eq(ev.args["deliverableHash"], expected):
        return "Submitted carries a deliverable hash the backend did not build"
    await transactions.mark_delivered(s, tx, _at(ev.args["releaseAfter"]))
    await fulfillment.mark_delivered(s, tx.id, ev.tx_hash, tx.delivered_at)
    await machine.apply(s, tx, Event.DELIVERED_ONCHAIN, f"chain:{ev.tx_hash}",
                        {"deliverable_hash": expected, "release_after": tx.release_after, "tx_hash": ev.tx_hash})
    return None


async def _dispute_opened(s: AsyncSession, tx, ev: DecodedLog) -> str | None:
    expected = await disputes.complaint_hash_for(s, tx.id)
    if not _hex_eq(ev.args["complaintHash"], expected):
        return "DisputeOpened carries a complaint hash that is not on file"
    await disputes.mark_open(s, tx.id)
    await machine.apply(s, tx, Event.DISPUTE_OPENED_ONCHAIN, f"chain:{ev.tx_hash}",
                        {"complaint_hash": expected, "tx_hash": ev.tx_hash})
    return None


async def _released(s: AsyncSession, tx, ev: DecodedLog) -> str | None:
    if int(ev.args["amount"]) != int(tx.amount_minor or -1):
        return "Released for an amount that is not the escrow amount"
    await payments.record(s, tx.id, "RELEASE", ev.tx_hash, int(ev.args["amount"]))
    await machine.apply(s, tx, Event.RELEASED_ONCHAIN, f"chain:{ev.tx_hash}",
                        {"amount_minor": int(ev.args["amount"]), "tx_hash": ev.tx_hash})
    return None


async def _resolved(s: AsyncSession, tx, ev: DecodedLog) -> str | None:
    settlement = await disputes.settlement_view(s, tx.id)
    if settlement is None:
        return "Resolved without a proposal on file"
    a = ev.args
    if not (_hex_eq(a["outcomeHash"], settlement["outcome_hash"])
            and int(a["toProvider"]) == settlement["to_provider_minor"]
            and int(a["toCustomer"]) == settlement["to_customer_minor"]):
        return "Resolved does not match the accepted proposal"
    await payments.record(s, tx.id, "SETTLE_PROVIDER", f"{ev.tx_hash}:provider", int(a["toProvider"]))
    await payments.record(s, tx.id, "SETTLE_CUSTOMER", f"{ev.tx_hash}:customer", int(a["toCustomer"]))
    await disputes.mark_settled(s, tx.id)
    await machine.apply(s, tx, Event.SETTLED_ONCHAIN, f"chain:{ev.tx_hash}",
                        {"provider_bps": settlement["provider_bps"], "to_provider_minor": int(a["toProvider"]),
                         "to_customer_minor": int(a["toCustomer"]), "outcome_hash": settlement["outcome_hash"],
                         "tx_hash": ev.tx_hash})
    return None


async def _refunded(s: AsyncSession, tx, ev: DecodedLog) -> str | None:
    await payments.record(s, tx.id, "REFUND", ev.tx_hash, int(ev.args["amount"]))
    tx.close_reason = "refunded"
    await machine.apply(s, tx, Event.REFUNDED_ONCHAIN, f"chain:{ev.tx_hash}",
                        {"amount_minor": int(ev.args["amount"]), "tx_hash": ev.tx_hash})
    return None


HANDLERS = {"JobFunded": _job_funded, "EvidenceAnchored": _evidence_anchored, "Submitted": _submitted,
            "DisputeOpened": _dispute_opened, "Released": _released, "Resolved": _resolved, "Refunded": _refunded}


async def handle_log(ev: DecodedLog) -> None:
    """One database transaction per log: the event row, the state change and its audit row commit together."""
    async with session_scope() as s:
        fresh = await payments.record_event(s, name=ev.name, tx_hash=ev.tx_hash, log_index=ev.log_index,
                                            block_number=ev.block_number, contract=ev.contract, tx_key=ev.tx_key,
                                            payload=ev.args)
        if not fresh:
            return                      # a replayed log changes nothing (FR-9)
        tx = await machine.lock_by_key(s, ev.tx_key)
        if tx is None:
            await payments.mark_event(s, ev.tx_hash, ev.log_index, handled=False,
                                      error="no transaction for this tx_key")
            log(logger, "chain event for an unknown transaction", event=ev.name, tx_key=ev.tx_key, tx_hash=ev.tx_hash)
            return
        transaction_id_var.set(str(tx.id))
        try:
            error = await HANDLERS[ev.name](s, tx, ev)
        except machine.IllegalTransition as err:
            error = f"{ev.name} is not allowed from {tx.state}: {err.message}"
        await payments.mark_event(s, ev.tx_hash, ev.log_index, handled=error is None, error=error)
        if error:
            await machine.note(s, tx, f"chain:{ev.tx_hash}", "EVENT_MISMATCH",
                               {"event": ev.name, "tx_hash": ev.tx_hash, "reason": error})
            log(logger, "chain event did not match", event=ev.name, tx_hash=ev.tx_hash, reason=error, state=tx.state)
        else:
            log(logger, "chain event applied", event=ev.name, tx_hash=ev.tx_hash, state=tx.state)


async def handle_raw_log(raw) -> None:
    decoded = await decode(raw)
    if decoded is not None:
        await handle_log(decoded)


async def head() -> int | None:
    try:
        return int(await arc_client.w3().eth.block_number)
    except Exception:
        return None


async def receipt_logs(tx_hash: str) -> tuple[int, int]:
    """Fast path for the internal webhook: fetch one receipt and run its logs through the same handler."""
    receipt = await arc_client.w3().eth.get_transaction_receipt(tx_hash)
    for raw in receipt["logs"]:
        await handle_raw_log(raw)
    return len(receipt["logs"]), int(receipt["status"])


async def _cursor() -> int:
    """First run starts at ESCROW_DEPLOY_BLOCK. With no deploy block configured, start at the head rather than
    crawling a chain that is millions of blocks long and cannot contain any of our events."""
    async with session_scope() as s:
        row = await s.get(KvCursor, CURSOR_KEY)
    if row is not None:
        return int(row.value)
    configured = get_settings().escrow_deploy_block
    if configured > 0:
        return configured
    current = await head()
    start = current if current is not None else 0
    await _set_cursor(start)
    return start


async def _set_cursor(value: int) -> None:
    async with session_scope() as s:
        row = await s.get(KvCursor, CURSOR_KEY)
        if row is None:
            s.add(KvCursor(key=CURSOR_KEY, value=str(value)))
        else:
            row.value, row.updated_at = str(value), utcnow()
            s.add(row)


async def lag_blocks() -> int | None:
    current = await head()
    return None if current is None else max(0, current - await _cursor())


async def poll_once() -> int:
    s_ = get_settings()
    chain_head = await head()
    if chain_head is None:
        return 0
    limit = chain_head - s_.confirmations
    start = await _cursor()
    if limit < start:
        return 0
    end = min(limit, start + s_.log_range_blocks - 1)
    try:
        logs = await arc_client.w3().eth.get_logs({"address": arc_client.checksum(s_.escrow_address),
                                                   "fromBlock": start, "toBlock": end})
    except Exception as err:
        if "pruned" not in str(err).lower():
            raise
        await _set_cursor(limit)
        log(logger, "watcher skipped pruned history", start=start, resumed_at=limit)
        return 0
    for raw in logs:
        await handle_raw_log(raw)
    await _set_cursor(end + 1)
    return len(logs)


async def run(stop: asyncio.Event) -> None:
    interval = get_settings().watch_interval_seconds
    while not stop.is_set():
        try:
            await poll_once()
        except Exception as err:
            log(logger, "watcher poll failed", error=f"{type(err).__name__}: {err}")
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval)
        except TimeoutError:
            pass
