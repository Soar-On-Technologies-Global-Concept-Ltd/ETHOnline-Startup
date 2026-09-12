"""Resolver outbox: rows are written in the same DB transaction as the decision and sent afterwards, one at a time."""
import asyncio
import logging
import uuid

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from web3.exceptions import ContractLogicError, TimeExhausted

from app.core.config import get_settings
from app.core.db import session_scope
from app.core.hashing import hex_to_bytes
from app.core.logging import log
from app.core.columns import utcnow
from app.domains.payments.models import ChainTx
from app.integrations.arc import client as arc_client

logger = logging.getLogger("outbox")
RESOLVER_LOCK = asyncio.Lock()
WAKE = asyncio.Event()

CALLS = {
    # Everything the arbitrator key may send. It can propose a split and relay a signed resolution; it can never
    # move money on its own, because executeWithSignatures needs two distinct signers.
    "AI_PROPOSAL": ("submitAIProposal", lambda a: [int(a["intent_id"]), int(a["customer_amount"]),
                                                   int(a["provider_amount"])]),
    "EXECUTE": ("executeWithSignatures", lambda a: [int(a["intent_id"]), int(a["customer_amount"]),
                                                    int(a["provider_amount"]), hex_to_bytes(a["sig_a"]),
                                                    hex_to_bytes(a["sig_b"])]),
    "ABANDONMENT": ("executeAbandonment", lambda a: [int(a["intent_id"])]),
}


async def queue(s: AsyncSession, transaction_id: uuid.UUID | None, kind: str, args: dict) -> ChainTx:
    if kind not in CALLS:
        raise ValueError(f"unknown outbox kind {kind}")
    row = ChainTx(transaction_id=transaction_id, kind=kind, args=args)
    s.add(row)
    await s.flush()
    WAKE.set()
    return row


async def _fees() -> tuple[int, int]:
    w3 = arc_client.w3()
    floor = get_settings().min_max_fee_gwei * 10**9
    try:
        priority = int(await w3.eth.max_priority_fee)
    except Exception:
        priority = 10**9
    try:
        base = int((await w3.eth.get_block("latest")).get("baseFeePerGas") or 0)
    except Exception:
        base = 0
    return max(2 * base + priority, floor), priority


async def send_next() -> list | None:
    """Send the oldest QUEUED row. Returns the mined transaction's logs, or None when there was nothing to send.

    The logs are handed back rather than handled here: applying them is orchestration's job, and a domain never
    reaches up into it."""
    account = arc_client.resolver()
    if account is None:
        return None                      # no resolver key configured: nothing this loop can do
    w3 = arc_client.w3()
    async with RESOLVER_LOCK:
        async with session_scope() as s:
            row = (await s.exec(select(ChainTx).where(ChainTx.status == "QUEUED").order_by(ChainTx.id)
                                .with_for_update(skip_locked=True).limit(1))).first()
            if row is None:
                return None
            call = CALLS.get(row.kind)
            if call is None:
                # A kind this backend no longer sends: ANCHOR, OPEN_DISPUTE and RESOLVE went with the old escrow.
                # Retire the row rather than raising, or one stale row wedges the sender for every other one.
                row.status, row.error = "FAILED", f"{row.kind} is not a call this backend makes any more"
                s.add(row)
                log(logger, "outbox row retired", kind=row.kind, id=row.id)
                return []
            fn_name, build_args = call
            row.attempts += 1
            try:
                max_fee, priority = await _fees()
                nonce = await w3.eth.get_transaction_count(account.address, "pending")
                fn = getattr(arc_client.escrow().functions, fn_name)(*build_args(row.args))
                tx = await fn.build_transaction({"from": account.address, "nonce": nonce, "chainId": get_settings().arc_chain_id,
                                                 "maxFeePerGas": max_fee, "maxPriorityFeePerGas": priority})
                signed = account.sign_transaction(tx)
                tx_hash = "0x" + bytes(await w3.eth.send_raw_transaction(signed.raw_transaction)).hex()
            except ContractLogicError as err:
                row.status, row.error = "FAILED", f"revert: {err}"
                s.add(row)
                log(logger, "outbox tx would revert", kind=row.kind, id=row.id, error=str(err))
                return []
            except Exception as err:
                row.error = f"send failed: {err}"
                s.add(row)
                log(logger, "outbox send failed; will retry", kind=row.kind, id=row.id, error=str(err))
                return []
            row.tx_hash, row.nonce, row.status, row.sent_at = tx_hash.lower(), nonce, "SENT", utcnow()
            s.add(row)
            row_id = row.id
    return await confirm(row_id, tx_hash)


async def confirm(row_id: int, tx_hash: str, timeout: float = 30.0) -> None:
    try:
        receipt = await arc_client.w3().eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)
    except TimeExhausted:
        return
    async with session_scope() as s:
        row = await s.get(ChainTx, row_id)
        row.status = "MINED" if receipt["status"] == 1 else "FAILED"
        row.mined_at = utcnow()
        if row.status == "FAILED":
            row.error = "reverted on-chain"
        s.add(row)
    return list(receipt["logs"])


async def recheck_sent(stuck_after_seconds: int = 120) -> list:
    """After a restart or a timeout: re-check SENT rows; mark STUCK when no receipt appears."""
    async with session_scope() as s:
        rows = (await s.exec(select(ChainTx).where(ChainTx.status == "SENT"))).all()
        pending = [(r.id, r.tx_hash, r.sent_at) for r in rows]
    found: list = []
    for row_id, tx_hash, sent_at in pending:
        try:
            receipt = await arc_client.w3().eth.get_transaction_receipt(tx_hash)
        except Exception:
            receipt = None
        if receipt is not None:
            found.extend(await confirm(row_id, tx_hash, timeout=1))
        elif sent_at and (utcnow() - sent_at).total_seconds() > stuck_after_seconds:
            async with session_scope() as s:
                row = await s.get(ChainTx, row_id)
                row.status, row.error = "STUCK", "no receipt after 120 s"
                s.add(row)
            log(logger, "outbox tx stuck", id=row_id, tx_hash=tx_hash)
    return found
