"""Deadlines fire without a human, and only when they should (schematics §9.3). Marked `db`."""
import uuid
from datetime import timedelta

import pytest
from sqlmodel import SQLModel

from app.core.db import dispose_engine, get_engine, session_scope, sessionmaker
from app.core.states import TxState
from app.core.columns import utcnow
from app.domains.authorization.models import Authorization
from app.domains.disputes.models import Complaint, Dispute, ResolutionProposal
from app.domains.identity.models import HumanCheck, User
from app.domains.intents.models import Intent
from app.domains.payments.models import Payment
from app.domains.providers.models import Provider
from app.domains.transactions.models import Transaction
from app.workers import reconciliation

pytestmark = pytest.mark.db

TABLES = ("audit_events, blockchain_events, resolution_acceptances, resolution_proposals, disputes, complaints, evidence, "
          "chain_txs, idempotency_keys, fulfillments, payments, authorizations, human_checks, transactions, quotes, "
          "intents, providers, users, kv_cursors")


@pytest.fixture
async def db():
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        await conn.exec_driver_sql(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE")
    yield
    await dispose_engine()


async def make(state: TxState, **fields) -> uuid.UUID:
    async with session_scope() as s:
        customer = User(privy_did=f"did:privy:{uuid.uuid4()}")
        s.add(customer)
        await s.flush()
        provider = Provider(display_name="Tunde's Painting", trade="painting", areas=["Surulere"],
                            base_rate_minor=8_250_000, verified=True)
        s.add(provider)
        intent = Intent(customer_id=customer.id, raw_text="Paint a 2-bedroom", status="STRUCTURED")
        s.add(intent)
        await s.flush()
        tx = Transaction(tx_key="0x" + uuid.uuid4().hex + uuid.uuid4().hex, intent_id=intent.id, customer_id=customer.id,
                         provider_id=provider.id, state=state.value, amount_minor=100_000_000,
                         display_amount_minor=16_500_000, fx_rate_ngn_per_usdc=1650, **fields)
        s.add(tx)
        await s.flush()
        return tx.id


async def add_authorization(tx_id: uuid.UUID, expires_at) -> None:
    async with session_scope() as s:
        tx = await s.get(Transaction, tx_id)
        check = HumanCheck(user_id=tx.customer_id, transaction_id=tx.id, action="authorize-transaction",
                           nullifier=uuid.uuid4().int % 10**30, scope_key=str(tx.id))
        s.add(check)
        await s.flush()
        s.add(Authorization(transaction_id=tx.id, version=1, typed_data={}, signature="0x" + "00" * 65,
                            signer="0x" + "11" * 20, authorization_hash="0x" + uuid.uuid4().hex * 2,
                            max_amount_minor=100_000_000, scope_hash="0x" + "33" * 32, provider_address="0x" + "22" * 20,
                            expires_at=expires_at, human_check_id=check.id, policy_decision={"decision": "ALLOW"}))


async def state_of(tx_id: uuid.UUID) -> Transaction:
    async with sessionmaker()() as s:
        return await s.get(Transaction, tx_id)


async def test_an_expired_authorization_cancels_the_transaction(db):
    tx_id = await make(TxState.AUTHORIZED)
    await add_authorization(tx_id, utcnow() - timedelta(minutes=1))
    assert await reconciliation.expire_authorizations() == 1
    tx = await state_of(tx_id)
    assert tx.state == TxState.CANCELLED.value and tx.close_reason == "authorization_expired"
    assert tx.closed_at is not None


async def test_a_live_authorization_is_left_alone(db):
    tx_id = await make(TxState.AUTHORIZED)
    await add_authorization(tx_id, utcnow() + timedelta(minutes=10))
    assert await reconciliation.expire_authorizations() == 0
    assert (await state_of(tx_id)).state == TxState.AUTHORIZED.value


async def test_a_pending_funding_transaction_is_never_cancelled(db):
    """The money may already be in flight; cancelling here would strand it."""
    tx_id = await make(TxState.FUNDING)
    await add_authorization(tx_id, utcnow() - timedelta(minutes=1))
    async with session_scope() as s:
        s.add(Payment(transaction_id=tx_id, rail="arc", direction="FUND", external_ref="0x" + "ab" * 32,
                      status="PENDING", amount_minor=100_000_000))
    assert await reconciliation.expire_authorizations() == 0
    assert (await state_of(tx_id)).state == TxState.FUNDING.value


async def test_a_missed_response_deadline_moves_the_dispute_on(db, fake_llm):
    tx_id = await make(TxState.DISPUTED, release_after=utcnow() + timedelta(minutes=5))
    async with session_scope() as s:
        tx = await s.get(Transaction, tx_id)
        check = HumanCheck(user_id=tx.customer_id, transaction_id=tx.id, action="file-complaint",
                           nullifier=uuid.uuid4().int % 10**30, scope_key=str(tx.id))
        s.add(check)
        await s.flush()
        complaint = Complaint(transaction_id=tx.id, filed_by=tx.customer_id, category="INCOMPLETE", text="one coat",
                              evidence_ids=[], complaint_hash="0x" + "44" * 32, human_check_id=check.id)
        s.add(complaint)
        await s.flush()
        s.add(Dispute(transaction_id=tx.id, complaint_id=complaint.id, status="OPEN",
                      response_deadline=utcnow() - timedelta(minutes=1)))
    assert await reconciliation.response_timeouts() == 1
    assert (await state_of(tx_id)).state == TxState.RESOLVING.value


async def test_a_missed_acceptance_deadline_escalates(db):
    tx_id = await make(TxState.PROPOSED)
    async with session_scope() as s:
        tx = await s.get(Transaction, tx_id)
        check = HumanCheck(user_id=tx.customer_id, transaction_id=tx.id, action="file-complaint",
                           nullifier=uuid.uuid4().int % 10**30, scope_key=str(tx.id))
        s.add(check)
        await s.flush()
        complaint = Complaint(transaction_id=tx.id, filed_by=tx.customer_id, category="INCOMPLETE", text="one coat",
                              evidence_ids=[], complaint_hash="0x" + "55" * 32, human_check_id=check.id)
        s.add(complaint)
        await s.flush()
        dispute = Dispute(transaction_id=tx.id, complaint_id=complaint.id, status="PROPOSED", level="L2")
        s.add(dispute)
        await s.flush()
        s.add(ResolutionProposal(dispute_id=dispute.id, level="L2", remedy="SPLIT_70_30", provider_bps=7000,
                                 to_provider_minor=70_000_000, to_customer_minor=30_000_000, rationale="because",
                                 cited_evidence_ids=[], outcome_hash="0x" + "66" * 32, status="OPEN",
                                 accept_deadline=utcnow() - timedelta(minutes=1)))
    assert await reconciliation.acceptance_timeouts() == 1
    tx = await state_of(tx_id)
    assert tx.state == TxState.ESCALATED.value
    async with sessionmaker()() as s:
        dispute = (await s.exec(__import__("sqlmodel").select(Dispute).where(Dispute.transaction_id == tx_id))).one()
        assert dispute.status == "ESCALATED"


async def test_a_complaint_that_lost_the_race_is_closed_honestly(db):
    tx_id = await make(TxState.RELEASED)
    async with session_scope() as s:
        tx = await s.get(Transaction, tx_id)
        check = HumanCheck(user_id=tx.customer_id, transaction_id=tx.id, action="file-complaint",
                           nullifier=uuid.uuid4().int % 10**30, scope_key=str(tx.id))
        s.add(check)
        await s.flush()
        complaint = Complaint(transaction_id=tx.id, filed_by=tx.customer_id, category="INCOMPLETE", text="too late",
                              evidence_ids=[], complaint_hash="0x" + "77" * 32, human_check_id=check.id)
        s.add(complaint)
        await s.flush()
        s.add(Dispute(transaction_id=tx.id, complaint_id=complaint.id, status="OPENING"))
    assert await reconciliation.close_late_disputes() == 1
    async with sessionmaker()() as s:
        dispute = (await s.exec(__import__("sqlmodel").select(Dispute).where(Dispute.transaction_id == tx_id))).one()
        assert dispute.status == "TOO_LATE"
    assert (await state_of(tx_id)).state == TxState.RELEASED.value
