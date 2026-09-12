"""The resolver key does workflow steps only: anchor evidence, open a dispute, release after the window, relay a signed resolution.
It cannot redirect funds, change amounts or settle without both signatures — the contract checks that."""
import uuid

from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.payments.models import ChainTx
from app.domains.payments import outbox
from app.integrations.arc import client as arc_client


def address() -> str | None:
    account = arc_client.resolver()
    return account.address if account else None


async def queue_anchor(s: AsyncSession, tx_id: uuid.UUID, tx_key: str, evidence_hash: str) -> ChainTx:
    return await outbox.queue(s, tx_id, "ANCHOR", {"tx_key": tx_key, "evidence_hash": evidence_hash})


async def queue_open_dispute(s: AsyncSession, tx_id: uuid.UUID, tx_key: str, complaint_hash: str) -> ChainTx:
    return await outbox.queue(s, tx_id, "OPEN_DISPUTE", {"tx_key": tx_key, "complaint_hash": complaint_hash})


async def queue_release(s: AsyncSession, tx_id: uuid.UUID, tx_key: str) -> ChainTx:
    return await outbox.queue(s, tx_id, "RELEASE", {"tx_key": tx_key})


async def queue_resolve(s: AsyncSession, tx_id: uuid.UUID, tx_key: str, provider_bps: int, outcome_hash: str,
                        sig_customer: str, sig_provider: str) -> ChainTx:
    return await outbox.queue(s, tx_id, "RESOLVE", {"tx_key": tx_key, "provider_bps": provider_bps, "outcome_hash": outcome_hash,
                                                    "sig_customer": sig_customer, "sig_provider": sig_provider})
