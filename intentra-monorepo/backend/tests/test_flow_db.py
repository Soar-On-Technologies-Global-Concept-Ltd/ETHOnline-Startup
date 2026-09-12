"""Both demo paths, end to end, against a real database with synthetic escrow events (PRD success criterion).

Marked `db`: needs Postgres. Run with  pytest -m db
"""
import io
import uuid

import pytest
from eth_account import Account
from eth_account.messages import encode_typed_data
from PIL import Image
from sqlmodel import SQLModel, select

from app.core.config import get_settings
from app.core.db import dispose_engine, get_engine, session_scope, sessionmaker
from app.core.states import EvidenceKind, TxState
from app.domains.authorization import service as authorization
from app.domains.disputes import service as disputes
from app.domains.disputes.models import Dispute
from app.domains.evidence import service as evidence_service
from app.domains.fulfillment import service as fulfillment
from app.domains.identity.models import User
from app.domains.intents import service as intents
from app.domains.intents.ai import ParsedIntent
from app.domains.payments import service as payments
from app.domains.payments.models import ChainTx, Payment
from app.domains.providers import service as providers
from app.domains.providers.models import Provider
from app.domains.transactions import machine
from app.domains.transactions import service as transactions
from app.domains.transactions import views
from app.domains.transactions.models import Transaction
from app.integrations.arc import eip712
from app.integrations.arc.events import DecodedLog
from app.orchestration.chain_events import handle_log

pytestmark = pytest.mark.db

CUSTOMER_KEY = "0x" + "a1" * 32
PROVIDER_KEY = "0x" + "b2" * 32
TABLES = ("audit_events, blockchain_events, resolution_acceptances, resolution_proposals, disputes, complaints, evidence, "
          "chain_txs, idempotency_keys, fulfillments, payments, authorizations, human_checks, transactions, quotes, "
          "intents, providers, users, kv_cursors")
SPEC = {"service": "painting", "area": "Surulere", "rooms": 2, "budget_max_minor": 18_000_000, "currency": "NGN",
        "date": "2026-09-12", "requirements": ["2 coats", "paint included"]}


@pytest.fixture
async def db():
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        await conn.exec_driver_sql(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE")
    yield
    await dispose_engine()


def photo(colour: tuple[int, int, int]) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (48, 32), colour).save(out, format="JPEG")
    return out.getvalue()


def proof() -> dict:
    return {"fake": True, "nullifier": str(uuid.uuid4().int)}


def sign(key: str, typed: dict) -> str:
    return "0x" + bytes(Account.sign_message(encode_typed_data(full_message=typed), private_key=key).signature).hex()


def chain_event(name: str, intent_id: int, args: dict, index: int = 0, tx_hash: str | None = None) -> DecodedLog:
    """The canonical escrow keys everything on intentId; IntentCreated is matched by the reported hash instead."""
    return DecodedLog(name=name, tx_hash=(tx_hash or ("0x" + uuid.uuid4().hex + uuid.uuid4().hex)).lower(),
                      log_index=index, block_number=100 + index, contract=get_settings().escrow_address.lower(),
                      tx_key=str(intent_id), args={"intentId": int(intent_id), **args})


def reported_hash() -> str:
    return "0x" + uuid.uuid4().hex + uuid.uuid4().hex


async def setup_parties(s) -> tuple[User, User, Provider]:
    customer = User(privy_did="did:privy:ada", email="ada@intentra.demo", display_name="Ada",
                    wallet_address=Account.from_key(CUSTOMER_KEY).address.lower())
    provider_user = User(privy_did="did:privy:tunde", email="tunde@intentra.demo", role="provider", display_name="Tunde",
                         wallet_address=Account.from_key(PROVIDER_KEY).address.lower())
    s.add(customer)
    s.add(provider_user)
    await s.flush()
    provider = Provider(user_id=provider_user.id, email="tunde@intentra.demo", display_name="Tunde's Painting",
                        trade="painting", areas=["Surulere"], base_rate_minor=8_250_000, verified=True, seeded=True)
    s.add(provider)
    await s.flush()
    return customer, provider_user, provider


async def walk_to_delivered(fake_llm) -> dict:
    """intent → quote → authorize → fund → start → evidence → deliver, committing money states only on events."""
    async with session_scope() as s:
        customer, provider_user, provider = await setup_parties(s)
        intent, tx = await intents.capture(s, customer.id, "Paint a 2-bedroom in Surulere under ₦180k this Saturday",
                                           ParsedIntent(SPEC, None, "fake-llm", "test"))
        quote = await intents.upsert_quote(s, intent, provider.id, provider.display_name, SPEC, 16_500_000,
                                           {"score": 82}, 1)
        ids = {"customer": customer.id, "provider_user": provider_user.id, "provider": provider.id,
               "tx": tx.id, "quote": quote.id, "tx_key": tx.tx_key}

    async with session_scope() as s:
        tx = await machine.lock(s, ids["tx"])
        status, body = await transactions.select_quote(
            s, tx, ids["customer"], await intents.quote_view(s, ids["quote"]),
            await providers.summary(s, ids["provider"]),
            Account.from_key(CUSTOMER_KEY).address, Account.from_key(PROVIDER_KEY).address)
        assert status == 201 and tx.state == TxState.AWAITING_AUTHORIZATION.value
        assert tx.amount_minor == 100_000_000 and tx.display_amount_minor == 16_500_000
        typed = tx.authorization_offer["typed_data"]
        digest = tx.authorization_offer["digest"]

    signature = sign(CUSTOMER_KEY, typed)
    async with sessionmaker()() as s:
        signer, human, offered = await authorization.verify(await s.get(Transaction, ids["tx"]), signature, proof())
    assert offered == digest

    async with session_scope() as s:
        tx = await machine.lock(s, ids["tx"])
        status, _ = await authorization.record(s, tx, ids["customer"], signature, signer, digest, human)
        assert status == 200 and tx.state == TxState.AUTHORIZED.value

    # Phase one: the escrow assigns the id, so the wallet sends createIntent and reports the hash.
    async with session_scope() as s:
        tx = await machine.lock(s, ids["tx"])
        _, body = await payments.fund_calls(s, tx, ids["customer"], Account.from_key(PROVIDER_KEY).address)
        assert body["step"] == "create_intent" and body["calls"][0]["fn"] == "createIntent"
        assert tx.state == TxState.FUNDING.value
    create_hash = reported_hash()
    async with session_scope() as s:
        tx = await machine.lock(s, ids["tx"])
        await payments.report_chain_tx(s, tx, ids["customer"], "CREATE_INTENT", create_hash)
    ids["intent_id"] = 41
    await handle_log(chain_event("IntentCreated", ids["intent_id"], tx_hash=create_hash,
                                 args={"customer": Account.from_key(CUSTOMER_KEY).address.lower(),
                                       "provider": Account.from_key(PROVIDER_KEY).address.lower(),
                                       "token": get_settings().usdc_address.lower(), "amount": 100_000_000}))
    async with sessionmaker()() as s:
        assert (await s.get(Transaction, ids["tx"])).escrow_intent_id == ids["intent_id"]

    # Phase two: approve and fund, then the escrow confirms it holds the money.
    async with session_scope() as s:
        tx = await machine.lock(s, ids["tx"])
        _, body = await payments.fund_calls(s, tx, ids["customer"], Account.from_key(PROVIDER_KEY).address)
        assert body["step"] == "fund_intent" and [c["fn"] for c in body["calls"]] == ["approve", "fundIntent"]
    await handle_log(chain_event("IntentFunded", ids["intent_id"], {"amount": 100_000_000}, index=1))
    async with sessionmaker()() as s:
        assert (await s.get(Transaction, ids["tx"])).state == TxState.FUNDED.value

    async with session_scope() as s:
        tx = await machine.lock(s, ids["tx"])
        await fulfillment.start(s, tx, ids["provider_user"])
        assert tx.state == TxState.IN_PROGRESS.value

    for index, room in enumerate(("bedroom_1", "bedroom_2")):
        stored = await evidence_service.store(photo((10 * index + 10, 90, 60)), ids["tx"])
        async with session_scope() as s:
            tx = await machine.lock(s, ids["tx"])
            await evidence_service.record(s, tx, ids["provider_user"], "provider", EvidenceKind.AFTER_PHOTO, room,
                                          f"{room} second coat", stored)

    async with sessionmaker()() as s:
        assert (await s.get(Transaction, ids["tx"])).state == TxState.EVIDENCE_SUBMITTED.value

    # There is no submit() on the canonical escrow: delivery is Intentra's own record.
    async with session_scope() as s:
        tx = await machine.lock(s, ids["tx"])
        _, body = await fulfillment.deliver_call(s, tx, ids["provider_user"])
        ids["deliverable_hash"] = body["deliverable_hash"]
        assert tx.state == TxState.DELIVERED.value
    return ids


async def test_the_happy_path_ends_with_the_provider_paid(db, fake_llm):
    ids = await walk_to_delivered(fake_llm)
    # Paying the provider in full is a resolution: the customer signs, the arbitrator co-signs, the resolver relays.
    async with session_scope() as s:
        tx = await machine.lock(s, ids["tx"])
        _, body = await payments.release_request(s, tx, ids["customer"])
        typed = eip712.resolution_typed_data(ids["intent_id"], 0, 100_000_000)
        assert body["split"] == {"to_provider_minor": 100_000_000, "to_customer_minor": 0}
    async with session_scope() as s:
        tx = await machine.lock(s, ids["tx"])
        status, _ = await payments.release_execute(s, tx, ids["customer"], sign(CUSTOMER_KEY, typed),
                                                   Account.from_key(CUSTOMER_KEY).address.lower())
        assert status == 202
    async with sessionmaker()() as s:
        queued = list((await s.exec(select(ChainTx).where(ChainTx.kind == "EXECUTE"))).all())
        assert len(queued) == 1 and queued[0].args["provider_amount"] == 100_000_000

    await handle_log(chain_event("IntentResolved", ids["intent_id"],
                                 {"customerAmount": 0, "providerAmount": 100_000_000}, index=4))
    async with sessionmaker()() as s:
        tx = await s.get(Transaction, ids["tx"])
        assert tx.state == TxState.RELEASED.value and tx.closed_at is not None
        rows = {p.direction: p.status for p in (await s.exec(select(Payment).where(Payment.transaction_id == tx.id))).all()}
        # createIntent is reported by the wallet and stays PENDING: it is how IntentCreated found this job, not a payment.
        assert rows == {"CREATE_INTENT": "PENDING", "FUND": "CONFIRMED", "RELEASE": "CONFIRMED"}
        timeline = await views.timeline(s, tx)
        assert timeline["verification"]["verified"] is True
        assert [e["event"] for e in timeline["events"]][:2] == ["TRANSACTION_CREATED", "INTENT_STRUCTURED"]
        assert timeline["events"][-1]["to"] == "RELEASED"


async def test_the_dispute_path_settles_seventy_thirty(db, fake_llm):
    ids = await walk_to_delivered(fake_llm)
    stored = await evidence_service.store(photo((200, 30, 30)), ids["tx"])
    async with session_scope() as s:
        tx = await machine.lock(s, ids["tx"])
        row, _ = await evidence_service.record(s, tx, ids["customer"], "customer", EvidenceKind.COMPLAINT, None,
                                               "Second bedroom has one coat", stored)
        complaint_evidence = row.id

    async with sessionmaker()() as s:
        human = await disputes.verify_complaint(await s.get(Transaction, ids["tx"]), proof())
    async with session_scope() as s:
        tx = await machine.lock(s, ids["tx"])
        status, body = await disputes.file_complaint(s, tx, ids["customer"], "INCOMPLETE",
                                                     "Second bedroom only got one coat", [complaint_evidence], human)
        assert status == 202
        assert body["call"]["fn"] == "raiseDispute"      # only a party may freeze the money on-chain
        dispute_id = uuid.UUID(body["dispute"]["id"])

    await handle_log(chain_event("DisputeRaised", ids["intent_id"],
                                 {"raisedBy": Account.from_key(CUSTOMER_KEY).address.lower()}, index=5))
    async with sessionmaker()() as s:
        tx = await s.get(Transaction, ids["tx"])
        assert tx.state == TxState.DISPUTED.value
        assert (await s.get(Dispute, dispute_id)).response_deadline is not None

    async with session_scope() as s:
        tx = await machine.lock(s, ids["tx"])
        await disputes.respond(s, tx, await s.get(Dispute, dispute_id), ids["provider_user"],
                               "I applied two coats in both rooms; here are the photos.")
        assert tx.state == TxState.RESOLVING.value

    await disputes.run_ladder(dispute_id)
    async with sessionmaker()() as s:
        tx = await s.get(Transaction, ids["tx"])
        assert tx.state == TxState.PROPOSED.value
        proposal = await disputes.proposal_for(s, dispute_id)
        assert (proposal.remedy, proposal.provider_bps) == ("SPLIT_70_30", 7000)
        assert (proposal.to_provider_minor, proposal.to_customer_minor) == (70_000_000, 30_000_000)
        assert proposal.to_provider_minor + proposal.to_customer_minor == tx.amount_minor
        typed = eip712.resolution_typed_data(tx.escrow_intent_id, proposal.to_customer_minor,
                                            proposal.to_provider_minor)
        proposal_id = proposal.id

    for key, role, user_key in ((CUSTOMER_KEY, "customer", "customer"), (PROVIDER_KEY, "provider", "provider_user")):
        async with session_scope() as s:
            tx = await machine.lock(s, ids["tx"])
            proposal = await disputes.proposal_for(s, dispute_id)
            status, body = await disputes.accept(s, tx, await s.get(Dispute, dispute_id), proposal,
                                                 ids[user_key], role, sign(key, typed))
            assert status == 200
    assert body["status"] == "SETTLING" and body["pending_tx"] == "EXECUTE"

    async with sessionmaker()() as s:
        queued = list((await s.exec(select(ChainTx).where(ChainTx.kind == "EXECUTE"))).all())
        assert len(queued) == 1 and queued[0].status == "QUEUED"
        # exact amounts, not basis points: this is what both parties signed and what the contract will pay
        assert queued[0].args["provider_amount"] == 70_000_000
        assert queued[0].args["customer_amount"] == 30_000_000
        proposal = await disputes.proposal_for(s, dispute_id)

    await handle_log(chain_event("IntentResolved", ids["intent_id"],
                                 {"customerAmount": 30_000_000, "providerAmount": 70_000_000}, index=6))
    async with sessionmaker()() as s:
        tx = await s.get(Transaction, ids["tx"])
        assert tx.state == TxState.SETTLED.value
        paid = {p.direction: p.amount_minor for p in (await s.exec(select(Payment).where(Payment.transaction_id == tx.id))).all()}
        assert paid["SETTLE_PROVIDER"] == 70_000_000 and paid["SETTLE_CUSTOMER"] == 30_000_000
        assert (await views.timeline(s, tx))["verification"]["verified"] is True


async def test_a_replayed_log_changes_nothing(db, fake_llm):
    ids = await walk_to_delivered(fake_llm)
    event = chain_event("IntentResolved", ids["intent_id"], {"customerAmount": 0, "providerAmount": 100_000_000}, index=7)
    await handle_log(event)
    async with sessionmaker()() as s:
        first = await s.get(Transaction, ids["tx"])
        version, state = first.version, first.state
    await handle_log(event)
    await handle_log(event)
    async with sessionmaker()() as s:
        again = await s.get(Transaction, ids["tx"])
        assert (again.version, again.state) == (version, state)
        assert (await views.timeline(s, again))["verification"]["verified"] is True


async def test_a_mismatched_funding_event_is_refused(db, fake_llm):
    """An escrow that holds a different amount than the customer authorised must not move the state."""
    async with session_scope() as s:
        customer, provider_user, provider = await setup_parties(s)
        intent, tx = await intents.capture(s, customer.id, "Paint a 2-bedroom in Surulere",
                                           ParsedIntent(SPEC, None, "fake-llm", "test"))
        quote = await intents.upsert_quote(s, intent, provider.id, provider.display_name, SPEC, 16_500_000,
                                           {"score": 82}, 1)
        ids = {"customer": customer.id, "tx": tx.id, "quote": quote.id, "provider": provider.id}
    async with session_scope() as s:
        tx = await machine.lock(s, ids["tx"])
        await transactions.select_quote(s, tx, ids["customer"], await intents.quote_view(s, ids["quote"]),
                                        await providers.summary(s, ids["provider"]),
                                        Account.from_key(CUSTOMER_KEY).address, Account.from_key(PROVIDER_KEY).address)
        typed, digest = tx.authorization_offer["typed_data"], tx.authorization_offer["digest"]
    signature = sign(CUSTOMER_KEY, typed)
    async with sessionmaker()() as s:
        signer, human, _ = await authorization.verify(await s.get(Transaction, ids["tx"]), signature, proof())
    async with session_scope() as s:
        tx = await machine.lock(s, ids["tx"])
        await authorization.record(s, tx, ids["customer"], signature, signer, digest, human)
    async with session_scope() as s:
        tx = await machine.lock(s, ids["tx"])
        await payments.fund_calls(s, tx, ids["customer"], Account.from_key(PROVIDER_KEY).address)
    create_hash = reported_hash()
    async with session_scope() as s:
        tx = await machine.lock(s, ids["tx"])
        await payments.report_chain_tx(s, tx, ids["customer"], "CREATE_INTENT", create_hash)

    await handle_log(chain_event("IntentCreated", 99, tx_hash=create_hash,
                                 args={"customer": Account.from_key(CUSTOMER_KEY).address.lower(),
                                       "provider": Account.from_key(PROVIDER_KEY).address.lower(),
                                       "token": get_settings().usdc_address.lower(),
                                       "amount": 100_000_001}))          # one micro-USDC short of the mandate
    async with sessionmaker()() as s:
        tx = await s.get(Transaction, ids["tx"])
        assert tx.escrow_intent_id is None, "an intent for the wrong amount must not be bound"
        assert tx.state == TxState.FUNDING.value
        events = (await views.timeline(s, tx))["events"]
        assert events[-1]["event"] == "EVENT_MISMATCH"
