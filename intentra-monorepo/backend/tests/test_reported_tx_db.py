"""A reported transaction hash must not wait for the sweep to reach its block.

`report_chain_tx` records the wallet's hash as a hint so the receipt can be read early. After an idle restart
the watcher can be tens of thousands of blocks behind, and the client funding a job is blocked on the intentId
inside that receipt — so the hint has to be consumed on every tick, not when the sweep catches up. Marked `db`.
"""
import uuid
from datetime import timedelta

import pytest
from sqlmodel import SQLModel

import app.domains.registry  # noqa: F401  — registers every domain's tables on SQLModel.metadata
from app.core.columns import utcnow
from app.core.db import dispose_engine, get_engine, session_scope
from app.core.states import TxState
from app.domains.identity.models import User
from app.domains.intents.models import Intent
from app.domains.payments import service as payments
from app.domains.payments.models import BlockchainEvent, Payment
from app.domains.transactions.models import Transaction

pytestmark = pytest.mark.db

WINDOW = timedelta(minutes=10)
TABLES = ("audit_events, blockchain_events, chain_txs, payments, transactions, intents, users")


@pytest.fixture
async def db():
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        await conn.exec_driver_sql(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE")
    yield
    await dispose_engine()


async def a_transaction() -> uuid.UUID:
    async with session_scope() as s:
        customer = User(privy_did=f"did:privy:{uuid.uuid4()}")
        s.add(customer)
        await s.flush()
        intent = Intent(customer_id=customer.id, raw_text="Paint a 2-bedroom", status="STRUCTURED")
        s.add(intent)
        await s.flush()
        tx = Transaction(tx_key="0x" + uuid.uuid4().hex + uuid.uuid4().hex, intent_id=intent.id,
                         customer_id=customer.id, state=TxState.FUNDING.value, amount_minor=100_000_000,
                         display_amount_minor=16_500_000, fx_rate_ngn_per_usdc=1650)
        s.add(tx)
        await s.flush()
        return tx.id


async def report(tx_id: uuid.UUID, tx_hash: str, *, age: timedelta = timedelta(0)) -> None:
    async with session_scope() as s:
        s.add(Payment(transaction_id=tx_id, rail="arc", direction="FUND", external_ref=tx_hash,
                      status="PENDING", amount_minor=100_000_000, created_at=utcnow() - age))


async def test_a_freshly_reported_hash_is_offered_for_a_direct_receipt_read(db):
    tx_id = await a_transaction()
    tx_hash = "0x" + "ab" * 32
    await report(tx_id, tx_hash)
    async with session_scope() as s:
        assert await payments.unobserved_reported_hashes(s, WINDOW) == [tx_hash]


async def test_a_hash_whose_log_already_arrived_is_not_read_again(db):
    """The sweep and this pass overlap by design; once the event is stored there is nothing left to fetch."""
    tx_id = await a_transaction()
    tx_hash = "0x" + "cd" * 32
    await report(tx_id, tx_hash)
    async with session_scope() as s:
        s.add(BlockchainEvent(tx_hash=tx_hash, log_index=0, block_number=61719029, contract="0x" + "11" * 20,
                              name="IntentCreated", tx_key="7", payload={"intentId": 7}))
    async with session_scope() as s:
        assert await payments.unobserved_reported_hashes(s, WINDOW) == []


async def test_an_old_hash_stops_being_retried(db):
    """A send that reverted, or an ERC-20 approve, emits no escrow log at all — it must not be refetched forever."""
    tx_id = await a_transaction()
    await report(tx_id, "0x" + "ef" * 32, age=timedelta(minutes=30))
    async with session_scope() as s:
        assert await payments.unobserved_reported_hashes(s, WINDOW) == []


async def test_a_confirmed_payment_is_not_a_pending_hint(db):
    tx_id = await a_transaction()
    async with session_scope() as s:
        s.add(Payment(transaction_id=tx_id, rail="arc", direction="FUND", external_ref="0x" + "12" * 32,
                      status="CONFIRMED", amount_minor=100_000_000))
    async with session_scope() as s:
        assert await payments.unobserved_reported_hashes(s, WINDOW) == []
