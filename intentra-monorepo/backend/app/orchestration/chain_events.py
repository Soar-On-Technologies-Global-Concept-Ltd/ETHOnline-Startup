"""The chain decides money states. Escrow logs are read here and turned into state, through each domain's service.

The canonical IntentraEscrow keys everything on an auto-incrementing `intentId`, so the first job is binding that id
to our transaction: the customer's wallet sends `createIntent`, reports the hash, and the `IntentCreated` log on that
hash tells us which transaction it belongs to. Every later event is looked up by the id.
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
from app.domains.disputes import service as disputes
from app.domains.intents import service as intents
from app.domains.fulfillment import service as fulfillment
from app.domains.payments import service as payments
from app.domains.transactions import machine
from app.domains.transactions import service as transactions
from app.integrations.arc import client as arc_client
from app.integrations.arc.events import DecodedLog, decode

logger = logging.getLogger("chain")
CURSOR_KEY = "watcher_block"


def _at(seconds: int) -> datetime:
    return datetime.fromtimestamp(int(seconds), tz=timezone.utc)


async def _intent_created(s: AsyncSession, tx, ev: DecodedLog) -> str | None:
    """Binds the escrow's id to this transaction and records the amount the chain actually holds."""
    a = ev.args
    if int(a["amount"]) != int(tx.amount_minor or -1):
        return f"IntentCreated is for {a['amount']}, not the {tx.amount_minor} that was authorised"
    await transactions.bind_intent_id(s, tx, int(a["intentId"]))
    await machine.note(s, tx, f"chain:{ev.tx_hash}", "INTENT_CREATED",
                       {"intent_id": int(a["intentId"]), "amount_minor": int(a["amount"]), "tx_hash": ev.tx_hash})
    return None


async def _intent_funded(s: AsyncSession, tx, ev: DecodedLog) -> str | None:
    if int(ev.args["amount"]) != int(tx.amount_minor or -1):
        return "IntentFunded for an amount that is not the authorised amount"
    try:
        block = await arc_client.w3().eth.get_block(ev.block_number)
        when = _at(block["timestamp"])
    except Exception:
        when = utcnow()
    await transactions.mark_funded(s, tx, when)
    await payments.record(s, tx.id, "FUND", ev.tx_hash, int(ev.args["amount"]))
    quote = await intents.quote_view(s, tx.quote_id)
    await fulfillment.ensure(s, tx.id, list((quote["scope"] if quote else {}).get("checklist", [])))
    await machine.apply(s, tx, Event.FUNDED_ONCHAIN, f"chain:{ev.tx_hash}",
                        {"amount_minor": int(ev.args["amount"]), "tx_hash": ev.tx_hash, "block": ev.block_number})
    return None


async def _dispute_raised(s: AsyncSession, tx, ev: DecodedLog) -> str | None:
    if await disputes.for_transaction(s, tx.id) is None:
        return "DisputeRaised for a job with no complaint on file"
    await disputes.mark_open(s, tx.id)
    await machine.apply(s, tx, Event.DISPUTE_OPENED_ONCHAIN, f"chain:{ev.tx_hash}",
                        {"raised_by": ev.args.get("raisedBy"), "tx_hash": ev.tx_hash})
    return None


async def _ai_proposal_submitted(s: AsyncSession, tx, ev: DecodedLog) -> str | None:
    """The contract is now TIMELOCKED: either party has 48 hours to escalate to a human before this can execute."""
    expected = await disputes.settlement_view(s, tx.id)
    if expected is None:
        return "AIProposalSubmitted without a proposal on file"
    a = ev.args
    if int(a["customerAmount"]) != expected["to_customer_minor"] or int(a["providerAmount"]) != expected["to_provider_minor"]:
        return "AIProposalSubmitted does not match the proposal the backend recorded"
    await disputes.mark_timelocked(s, tx.id, _at(await _block_time(ev)))
    await machine.note(s, tx, f"chain:{ev.tx_hash}", "TX_MINED",
                       {"kind": "AI_PROPOSAL", "tx_hash": ev.tx_hash, "appeal_window_hours": 48})
    return None


async def _appeal_escalated(s: AsyncSession, tx, ev: DecodedLog) -> str | None:
    await disputes.mark_appealed(s, tx.id, ev.args.get("appellant"), int(ev.args.get("stake", 0)))
    await machine.apply(s, tx, Event.ESCALATION_REQUIRED, f"chain:{ev.tx_hash}",
                        {"appellant": ev.args.get("appellant"), "stake": int(ev.args.get("stake", 0)),
                         "tx_hash": ev.tx_hash})
    return None


async def _intent_resolved(s: AsyncSession, tx, ev: DecodedLog) -> str | None:
    """One event covers both endings: everything to the provider is a release, anything else is a settlement."""
    a = ev.args
    to_customer, to_provider = int(a["customerAmount"]), int(a["providerAmount"])
    total = int(tx.amount_minor or 0)
    if to_customer + to_provider != total:
        return f"IntentResolved pays {to_customer + to_provider}, not the {total} held in escrow"
    if to_customer == 0:
        await payments.record(s, tx.id, "RELEASE", ev.tx_hash, to_provider)
        await machine.apply(s, tx, Event.RELEASED_ONCHAIN, f"chain:{ev.tx_hash}",
                            {"amount_minor": to_provider, "tx_hash": ev.tx_hash})
        return None
    expected = await disputes.settlement_view(s, tx.id)
    if expected is not None and (expected["to_customer_minor"] != to_customer
                                 or expected["to_provider_minor"] != to_provider):
        return "IntentResolved does not match the accepted proposal"
    await payments.record(s, tx.id, "SETTLE_PROVIDER", f"{ev.tx_hash}:provider", to_provider)
    await payments.record(s, tx.id, "SETTLE_CUSTOMER", f"{ev.tx_hash}:customer", to_customer)
    await disputes.mark_settled(s, tx.id)
    await machine.apply(s, tx, Event.SETTLED_ONCHAIN, f"chain:{ev.tx_hash}",
                        {"to_provider_minor": to_provider, "to_customer_minor": to_customer, "tx_hash": ev.tx_hash})
    return None


async def _abandonment_executed(s: AsyncSession, tx, ev: DecodedLog) -> str | None:
    """Nobody acted for fourteen days, so the contract closed the job itself."""
    tx.close_reason = "abandoned"
    await machine.note(s, tx, f"chain:{ev.tx_hash}", "ABANDONMENT_EXECUTED",
                       {"triggered_by": ev.args.get("triggeredBy"), "tx_hash": ev.tx_hash})
    return None


async def _block_time(ev: DecodedLog) -> int:
    try:
        return int((await arc_client.w3().eth.get_block(ev.block_number))["timestamp"])
    except Exception:
        return int(utcnow().timestamp())


HANDLERS = {"IntentCreated": _intent_created, "IntentFunded": _intent_funded, "DisputeRaised": _dispute_raised,
            "AIProposalSubmitted": _ai_proposal_submitted, "AppealEscalated": _appeal_escalated,
            "IntentResolved": _intent_resolved, "AbandonmentExecuted": _abandonment_executed}


async def _transaction_for(s: AsyncSession, ev: DecodedLog):
    """IntentCreated is matched by the hash the wallet reported; everything after it by the escrow's own id."""
    if ev.name == "IntentCreated":
        return await payments.transaction_for_reported_tx(s, ev.tx_hash)
    return await machine.lock_by_intent_id(s, int(ev.args["intentId"]))


async def handle_log(ev: DecodedLog) -> None:
    """One database transaction per log: the event row, the state change and its audit row commit together."""
    async with session_scope() as s:
        fresh = await payments.record_event(s, name=ev.name, tx_hash=ev.tx_hash, log_index=ev.log_index,
                                            block_number=ev.block_number, contract=ev.contract,
                                            tx_key=str(ev.args.get("intentId", "")), payload=ev.args)
        if not fresh:
            return                      # a replayed log changes nothing (FR-9)
        tx = await _transaction_for(s, ev)
        if tx is None:
            await payments.mark_event(s, ev.tx_hash, ev.log_index, handled=False, error="no transaction for this intent")
            log(logger, "chain event for an unknown intent", event=ev.name, tx_hash=ev.tx_hash)
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
