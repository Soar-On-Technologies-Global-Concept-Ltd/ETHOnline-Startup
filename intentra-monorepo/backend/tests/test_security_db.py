"""The abuse cases, end to end over HTTP: someone lying about who they are, replaying a proof, reusing an
idempotency key, forging a signature or a link, or reaching for a transaction that is not theirs.

Marked `db`: needs Postgres. Run with  pytest -m db tests/test_security_db.py
"""
import hashlib
import hmac
import io
import json
import uuid

import pytest
from eth_account import Account
from eth_account.messages import encode_typed_data
from httpx import ASGITransport, AsyncClient
from PIL import Image
from sqlmodel import SQLModel

from app.core.config import get_settings
from app.core.db import dispose_engine, get_engine, session_scope
from app.domains.identity.models import User
from app.domains.providers.models import Provider
from app.integrations.arc.events import DecodedLog
from app.main import app
from app.orchestration.chain_events import handle_log

pytestmark = pytest.mark.db

TABLES = ("audit_events, blockchain_events, resolution_acceptances, resolution_proposals, disputes, complaints, evidence, "
          "chain_txs, idempotency_keys, fulfillments, payments, authorizations, human_checks, transactions, quotes, "
          "intents, providers, users, kv_cursors")
ADA = Account.from_key("0x" + "a1" * 32)
TUNDE = Account.from_key("0x" + "b2" * 32)
MALLORY = Account.from_key("0x" + "cc" * 32)
ADA_TOKEN = f"test:ada:{ADA.address}:ada@intentra.demo"
TUNDE_TOKEN = f"test:tunde:{TUNDE.address}:tunde@intentra.demo"
MALLORY_TOKEN = f"test:mallory:{MALLORY.address}:mallory@intentra.demo"


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def proof() -> dict:
    return {"fake": True, "nullifier": str(uuid.uuid4().int)}


def photo() -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (32, 24), (90, 120, 60)).save(out, format="JPEG")
    return out.getvalue()


@pytest.fixture
async def client():
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        await conn.exec_driver_sql(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http
    await dispose_engine()


@pytest.fixture
async def parties(client):
    """Ada (customer), Tunde (a verified provider with a wallet) and Mallory (a stranger with a valid session)."""
    async with session_scope() as s:
        provider_user = User(privy_did="did:privy:tunde", email="tunde@intentra.demo", role="provider",
                             display_name="Tunde", wallet_address=TUNDE.address.lower())
        s.add(provider_user)
        await s.flush()
        s.add(Provider(user_id=provider_user.id, email="tunde@intentra.demo", display_name="Tunde's Painting",
                       trade="painting", areas=["Surulere"], base_rate_minor=8_250_000, verified=True, seeded=True))
    for token in (ADA_TOKEN, TUNDE_TOKEN, MALLORY_TOKEN):
        assert (await client.post("/v1/auth/session", json={}, headers=auth(token))).status_code == 200


async def awaiting_authorization(client) -> dict:
    """Walk the real routes to a transaction that is waiting for Ada's signature."""
    intent = (await client.post("/v1/intents", json={"text": "Paint a 2-bedroom in Surulere under ₦180k this Saturday"},
                                headers=auth(ADA_TOKEN))).json()
    recommendations = (await client.get(f"/v1/providers/recommendations?intent_id={intent['intent_id']}",
                                        headers=auth(ADA_TOKEN))).json()
    quote = recommendations["items"][0]
    created = (await client.post("/v1/transactions", json={"intent_id": intent["intent_id"], "quote_id": quote["quote_id"]},
                                 headers=auth(ADA_TOKEN))).json()
    return created


async def in_progress(client) -> str:
    """Walk all the way to a started job: approved over HTTP, funded by a confirmed escrow event, then started."""
    created = await awaiting_authorization(client)
    tx_id = created["transaction"]["id"]
    signature = sign_authorization(created["authorization_typed_data"], ADA.key)
    approved = await client.post(f"/v1/transactions/{tx_id}/authorize",
                                 json={"signature": signature, "idkit_result": proof()},
                                 headers={**auth(ADA_TOKEN), "Idempotency-Key": str(uuid.uuid4())})
    assert approved.status_code == 200, approved.text
    # Funding is two phases on the canonical escrow: createIntent assigns the id, then approve + fundIntent.
    created = await client.post(f"/v1/transactions/{tx_id}/fund", json={},
                                headers={**auth(ADA_TOKEN), "Idempotency-Key": str(uuid.uuid4())})
    assert created.json()["step"] == "create_intent", created.text
    create_hash = "0x" + uuid.uuid4().hex * 2
    await client.post(f"/v1/transactions/{tx_id}/fund", json={"tx_hash": create_hash},
                      headers={**auth(ADA_TOKEN), "Idempotency-Key": str(uuid.uuid4())})
    intent_id = uuid.uuid4().int % 100_000
    await handle_log(DecodedLog(name="IntentCreated", tx_hash=create_hash, log_index=0, block_number=100,
                                contract=get_settings().escrow_address.lower(), tx_key=str(intent_id),
                                args={"intentId": intent_id, "customer": ADA.address.lower(),
                                      "provider": TUNDE.address.lower(),
                                      "token": get_settings().usdc_address.lower(), "amount": 100_000_000}))
    await handle_log(DecodedLog(name="IntentFunded", tx_hash="0x" + uuid.uuid4().hex * 2, log_index=0, block_number=101,
                                contract=get_settings().escrow_address.lower(), tx_key=str(intent_id),
                                args={"intentId": intent_id, "amount": 100_000_000}))
    started = await client.post(f"/v1/transactions/{tx_id}/start", headers=auth(TUNDE_TOKEN))
    assert started.status_code == 200, started.text
    return tx_id


def sign_authorization(typed: dict, key) -> str:
    typed = json.loads(json.dumps(typed))
    typed["message"]["maxAmount"] = int(typed["message"]["maxAmount"])
    return "0x" + bytes(Account.sign_message(encode_typed_data(full_message=typed), key).signature).hex()


# ---------------------------------------------------------------- who is calling

async def test_no_token_is_refused(client):
    response = await client.post("/v1/intents", json={"text": "Paint a 2-bedroom in Surulere"})
    assert response.status_code == 401 and response.json()["error"]["code"] == "invalid_token"


async def test_a_made_up_token_is_refused(client):
    response = await client.post("/v1/intents", json={"text": "Paint a 2-bedroom in Surulere"},
                                 headers=auth("Bearer-looking-nonsense"))
    assert response.status_code == 401


async def test_a_well_formed_token_without_a_session_is_refused(client):
    response = await client.get(f"/v1/transactions/{uuid.uuid4()}", headers=auth(MALLORY_TOKEN))
    assert response.status_code == 401 and response.json()["error"]["code"] == "session_required"


# ---------------------------------------------------------------- whose transaction is it

async def test_a_stranger_cannot_read_someone_elses_transaction(client, parties, fake_llm):
    created = await awaiting_authorization(client)
    tx_id = created["transaction"]["id"]
    assert (await client.get(f"/v1/transactions/{tx_id}", headers=auth(ADA_TOKEN))).status_code == 200
    response = await client.get(f"/v1/transactions/{tx_id}", headers=auth(MALLORY_TOKEN))
    assert response.status_code == 404, "a non-party must not learn that the transaction exists"
    assert "tx_key" not in response.text


async def test_a_stranger_cannot_read_the_timeline_or_the_evidence(client, parties, fake_llm):
    tx_id = (await awaiting_authorization(client))["transaction"]["id"]
    assert (await client.get(f"/v1/transactions/{tx_id}/timeline", headers=auth(MALLORY_TOKEN))).status_code == 404
    assert (await client.get(f"/v1/transactions/{tx_id}/evidence", headers=auth(MALLORY_TOKEN))).status_code == 404


async def test_the_customer_cannot_act_as_the_provider(client, parties, fake_llm):
    tx_id = (await awaiting_authorization(client))["transaction"]["id"]
    response = await client.post(f"/v1/transactions/{tx_id}/start", headers=auth(ADA_TOKEN))
    assert response.status_code == 403 and response.json()["error"]["code"] == "wrong_role"


async def test_the_provider_cannot_approve_the_payment(client, parties, fake_llm):
    created = await awaiting_authorization(client)
    tx_id = created["transaction"]["id"]
    response = await client.post(f"/v1/transactions/{tx_id}/authorize",
                                 json={"signature": "0x" + "11" * 65, "idkit_result": proof()},
                                 headers={**auth(TUNDE_TOKEN), "Idempotency-Key": str(uuid.uuid4())})
    assert response.status_code == 403 and response.json()["error"]["code"] == "wrong_role"


# ---------------------------------------------------------------- signatures and proofs

async def test_a_signature_from_the_wrong_wallet_is_refused(client, parties, fake_llm):
    created = await awaiting_authorization(client)
    tx_id = created["transaction"]["id"]
    forged = sign_authorization(created["authorization_typed_data"], MALLORY.key)
    response = await client.post(f"/v1/transactions/{tx_id}/authorize",
                                 json={"signature": forged, "idkit_result": proof()},
                                 headers={**auth(ADA_TOKEN), "Idempotency-Key": str(uuid.uuid4())})
    assert response.status_code == 403 and response.json()["error"]["code"] == "signature_mismatch"


async def test_a_selfie_check_cannot_be_replayed_on_the_same_job(client, parties, fake_llm):
    created = await awaiting_authorization(client)
    tx_id = created["transaction"]["id"]
    signature = sign_authorization(created["authorization_typed_data"], ADA.key)
    used = proof()
    first = await client.post(f"/v1/transactions/{tx_id}/authorize", json={"signature": signature, "idkit_result": used},
                              headers={**auth(ADA_TOKEN), "Idempotency-Key": str(uuid.uuid4())})
    assert first.status_code == 200
    again = await client.post(f"/v1/transactions/{tx_id}/authorize", json={"signature": signature, "idkit_result": used},
                              headers={**auth(ADA_TOKEN), "Idempotency-Key": str(uuid.uuid4())})
    assert again.status_code in (403, 409)
    if again.status_code == 403:
        assert again.json()["error"]["code"] == "human_check_failed"


# ---------------------------------------------------------------- replay and idempotency

async def test_a_money_route_demands_an_idempotency_key(client, parties, fake_llm):
    tx_id = (await awaiting_authorization(client))["transaction"]["id"]
    response = await client.post(f"/v1/transactions/{tx_id}/authorize",
                                 json={"signature": "0x" + "11" * 65, "idkit_result": proof()}, headers=auth(ADA_TOKEN))
    assert response.status_code == 422 and response.json()["error"]["details"]["header"] == "Idempotency-Key"


async def test_reusing_a_key_with_a_different_body_is_refused(client, parties, fake_llm):
    created = await awaiting_authorization(client)
    tx_id = created["transaction"]["id"]
    key = str(uuid.uuid4())
    signature = sign_authorization(created["authorization_typed_data"], ADA.key)
    first = await client.post(f"/v1/transactions/{tx_id}/authorize", json={"signature": signature, "idkit_result": proof()},
                              headers={**auth(ADA_TOKEN), "Idempotency-Key": key})
    assert first.status_code == 200
    reused = await client.post(f"/v1/transactions/{tx_id}/authorize",
                               json={"signature": "0x" + "22" * 65, "idkit_result": proof()},
                               headers={**auth(ADA_TOKEN), "Idempotency-Key": key})
    assert reused.status_code == 422 and reused.json()["error"]["code"] == "idempotency_key_reuse"


async def test_the_same_key_and_body_replays_instead_of_repeating_the_work(client, parties, fake_llm):
    created = await awaiting_authorization(client)
    tx_id = created["transaction"]["id"]
    key = str(uuid.uuid4())
    body = {"signature": sign_authorization(created["authorization_typed_data"], ADA.key), "idkit_result": proof()}
    first = await client.post(f"/v1/transactions/{tx_id}/authorize", json=body,
                              headers={**auth(ADA_TOKEN), "Idempotency-Key": key})
    second = await client.post(f"/v1/transactions/{tx_id}/authorize", json=body,
                               headers={**auth(ADA_TOKEN), "Idempotency-Key": key})
    assert first.status_code == 200 and second.status_code == 200
    assert second.headers.get("Idempotent-Replay") == "true"
    assert first.json()["authorization"]["id"] == second.json()["authorization"]["id"]


# ---------------------------------------------------------------- internal surfaces

async def test_the_internal_webhook_rejects_a_forged_signature(client):
    body = json.dumps({"tx_hash": "0x" + "ab" * 32}).encode()
    response = await client.post("/v1/webhooks/arc", content=body,
                                 headers={"Content-Type": "application/json", "X-Intentra-Signature": "deadbeef"})
    assert response.status_code == 401 and response.json()["error"]["code"] == "invalid_token"


async def test_the_simulator_does_not_exist_outside_development(client):
    """It is the one route that can move state without a chain, so it must be unreachable when ENV is not dev."""
    assert get_settings().env == "test"
    body = json.dumps({"name": "Released", "tx_key": "0x" + "11" * 32, "args": {}, "tx_hash": "0x" + "22" * 32}).encode()
    signature = hmac.new(get_settings().internal_webhook_secret.get_secret_value().encode(), body, hashlib.sha256).hexdigest()
    response = await client.post("/v1/webhooks/simulate", content=body,
                                 headers={"Content-Type": "application/json", "X-Intentra-Signature": signature})
    assert response.status_code == 404, "a correctly signed call must still be refused outside dev"


async def test_a_forged_evidence_link_is_refused(client):
    response = await client.get("/v1/files/some/photo.jpg?exp=99999999999&sig=deadbeef")
    assert response.status_code == 404


# ---------------------------------------------------------------- uploads

async def test_a_file_that_is_not_an_image_is_refused(client, parties, fake_llm):
    """The declared Content-Type is ignored: the format is sniffed from the bytes themselves."""
    tx_id = await in_progress(client)
    response = await client.post(f"/v1/transactions/{tx_id}/evidence", headers=auth(TUNDE_TOKEN),
                                 files={"file": ("payload.jpg", b"#!/bin/sh\nrm -rf /\n", "image/jpeg")},
                                 data={"kind": "AFTER_PHOTO", "scope_item": "bedroom_1"})
    assert response.status_code == 415 and response.json()["error"]["code"] == "unsupported_media_type"


async def test_a_real_photo_is_accepted_once_the_job_has_started(client, parties, fake_llm):
    tx_id = await in_progress(client)
    response = await client.post(f"/v1/transactions/{tx_id}/evidence", headers=auth(TUNDE_TOKEN),
                                 files={"file": ("after.jpg", photo(), "image/jpeg")},
                                 data={"kind": "AFTER_PHOTO", "scope_item": "bedroom_1"})
    assert response.status_code == 201 and response.json()["evidence"]["sha256"].startswith("0x")


async def test_the_customer_cannot_upload_the_providers_after_photos(client, parties, fake_llm):
    tx_id = await in_progress(client)
    response = await client.post(f"/v1/transactions/{tx_id}/evidence", headers=auth(ADA_TOKEN),
                                 files={"file": ("after.jpg", photo(), "image/jpeg")},
                                 data={"kind": "AFTER_PHOTO", "scope_item": "bedroom_1"})
    assert response.status_code == 403 and response.json()["error"]["code"] == "wrong_role"


async def test_a_photo_for_a_room_outside_the_agreed_scope_is_refused(client, parties, fake_llm):
    tx_id = await in_progress(client)
    response = await client.post(f"/v1/transactions/{tx_id}/evidence", headers=auth(TUNDE_TOKEN),
                                 files={"file": ("after.jpg", photo(), "image/jpeg")},
                                 data={"kind": "AFTER_PHOTO", "scope_item": "penthouse"})
    assert response.status_code == 422 and response.json()["error"]["code"] == "validation_error"


async def test_delivery_is_refused_until_every_room_is_covered(client, parties, fake_llm):
    """The provider cannot mark a job delivered by uploading one photo of two rooms."""
    tx_id = await in_progress(client)
    await client.post(f"/v1/transactions/{tx_id}/evidence", headers=auth(TUNDE_TOKEN),
                      files={"file": ("after.jpg", photo(), "image/jpeg")},
                      data={"kind": "AFTER_PHOTO", "scope_item": "bedroom_1"})
    response = await client.post(f"/v1/transactions/{tx_id}/deliver", json={},
                                 headers={**auth(TUNDE_TOKEN), "Idempotency-Key": str(uuid.uuid4())})
    assert response.status_code == 422 and response.json()["error"]["code"] == "insufficient_evidence"
    assert response.json()["error"]["details"]["missing"] == ["bedroom_2"]


async def test_a_stranger_cannot_upload_evidence(client, parties, fake_llm):
    tx_id = (await awaiting_authorization(client))["transaction"]["id"]
    response = await client.post(f"/v1/transactions/{tx_id}/evidence", headers=auth(MALLORY_TOKEN),
                                 files={"file": ("after.jpg", photo(), "image/jpeg")},
                                 data={"kind": "AFTER_PHOTO", "scope_item": "bedroom_1"})
    assert response.status_code == 404


async def test_evidence_is_refused_before_the_job_starts(client, parties, fake_llm):
    """An after-photo while the job is still awaiting approval is not evidence of anything."""
    tx_id = (await awaiting_authorization(client))["transaction"]["id"]
    response = await client.post(f"/v1/transactions/{tx_id}/evidence", headers=auth(TUNDE_TOKEN),
                                 files={"file": ("after.jpg", photo(), "image/jpeg")},
                                 data={"kind": "AFTER_PHOTO", "scope_item": "bedroom_1"})
    assert response.status_code == 409 and response.json()["error"]["code"] == "illegal_transition"
