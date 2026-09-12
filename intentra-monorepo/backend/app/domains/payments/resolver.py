"""The AI arbitrator key. It is one of the escrow's three signers, and it is deliberately not enough on its own:
`executeWithSignatures` needs two distinct signers, so this key can propose and relay, never unilaterally pay.
"""
import uuid

from eth_account import Account
from eth_account.messages import encode_typed_data
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.payments import outbox
from app.domains.payments.models import ChainTx
from app.integrations.arc import client as arc_client
from app.integrations.arc import eip712


def address() -> str | None:
    account = arc_client.resolver()
    return account.address if account else None


def co_sign(typed_data: dict) -> str:
    """The arbitrator's half of a 2-of-3 resolution. The other half is always a party's own wallet."""
    account = arc_client.resolver()
    if account is None:
        raise RuntimeError("no arbitrator key configured: set RESOLVER_PRIVATE_KEY")
    signed = Account.sign_message(encode_typed_data(full_message=typed_data), private_key=account.key)
    return "0x" + bytes(signed.signature).hex()


async def queue_ai_proposal(s: AsyncSession, tx_id: uuid.UUID, intent_id: int, customer_amount: int,
                            provider_amount: int) -> ChainTx:
    """Starts the contract's 48-hour appeal window. Either party may escalate to a human inside it."""
    return await outbox.queue(s, tx_id, "AI_PROPOSAL", {"intent_id": int(intent_id), "customer_amount": int(customer_amount),
                                                        "provider_amount": int(provider_amount)})


async def queue_execute(s: AsyncSession, tx_id: uuid.UUID, intent_id: int, customer_amount: int, provider_amount: int,
                        sig_a: str, sig_b: str) -> ChainTx:
    return await outbox.queue(s, tx_id, "EXECUTE", {"intent_id": int(intent_id), "customer_amount": int(customer_amount),
                                                    "provider_amount": int(provider_amount), "sig_a": sig_a, "sig_b": sig_b})


async def queue_abandonment(s: AsyncSession, tx_id: uuid.UUID, intent_id: int) -> ChainTx:
    """After the contract's 14-day timeout, anyone may force the intent to resolve."""
    return await outbox.queue(s, tx_id, "ABANDONMENT", {"intent_id": int(intent_id)})
