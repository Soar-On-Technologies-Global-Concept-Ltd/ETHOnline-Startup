"""Drives the whole demo against a running API: both paths, twice in a row, with no manual database edits.

    uvicorn app.main:app --reload            # ENV=dev, fake partner modes
    python scripts/demo_run.py --path both

The canonical IntentraEscrow assigns an `intentId`, so funding is two phases: the customer's wallet sends
`createIntent` and reports the hash, the backend learns the id from the `IntentCreated` log, and only then does it
hand back `approve` + `fundIntent`. Paying the provider in full is a resolution signed by the customer and
co-signed by the arbitrator, because the contract has no `release`.

With nothing deployed locally, chain events are fed to the same handler the watcher uses through the dev-only
/v1/webhooks/simulate route (ENV=dev, HMAC-signed). Against the live escrow, drop --simulate: the wallets send the
calls the API returns and the watcher applies the states from the real events.
"""
import argparse
import asyncio
import hashlib
import hmac
import io
import json
import os
import pathlib
import random
import sys
import time
import uuid

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import httpx  # noqa: E402
from eth_account import Account  # noqa: E402
from eth_account.messages import encode_typed_data  # noqa: E402
from eth_utils import keccak  # noqa: E402
from PIL import Image  # noqa: E402

BASE = os.getenv("DEMO_API", "http://127.0.0.1:8000")
SECRET = os.getenv("INTERNAL_WEBHOOK_SECRET", "dev-only-change-me")
ADA = Account.from_key(keccak(text="intentra-demo-ada"))
TUNDE = Account.from_key(keccak(text="intentra-demo-tunde"))
ADA_TOKEN = f"test:ada:{ADA.address}:ada@intentra.demo"
TUNDE_TOKEN = f"test:tunde:{TUNDE.address}:tunde@intentra.demo"


def say(step: str, detail: str = "") -> None:
    print(f"  {step:<34} {detail}")


def photo(colour: tuple[int, int, int]) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (320, 240), colour).save(out, format="JPEG")
    return out.getvalue()


def proof() -> dict:
    return {"fake": True, "nullifier": str(uuid.uuid4().int)}


def hash32() -> str:
    return "0x" + uuid.uuid4().hex * 2


def sign(typed: dict, account) -> str:
    typed = json.loads(json.dumps(typed))
    for field in ("maxAmount", "intentId", "customerAmount", "providerAmount"):
        if field in typed["message"]:
            typed["message"][field] = int(typed["message"][field])
    return "0x" + bytes(Account.sign_message(encode_typed_data(full_message=typed), account.key).signature).hex()


class Api:
    def __init__(self, client: httpx.AsyncClient, token: str):
        self.client, self.token = client, token

    async def call(self, method: str, path: str, *, json_body=None, idempotent=False, **kwargs):
        headers = {"Authorization": f"Bearer {self.token}"}
        if idempotent:
            headers["Idempotency-Key"] = str(uuid.uuid4())
        response = await self.client.request(method, BASE + path, json=json_body, headers=headers, **kwargs)
        if response.status_code >= 400:
            raise SystemExit(f"{method} {path} → {response.status_code} {response.text}")
        return response.json()


async def simulate(client: httpx.AsyncClient, name: str, intent_id: int, args: dict, tx_hash: str | None = None) -> None:
    body = json.dumps({"name": name, "tx_key": str(intent_id), "args": {"intentId": intent_id, **args},
                       "tx_hash": tx_hash or hash32(), "log_index": 0, "block_number": int(time.time())}).encode()
    signature = hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
    response = await client.post(BASE + "/v1/webhooks/simulate", content=body,
                                 headers={"Content-Type": "application/json", "X-Intentra-Signature": signature})
    if response.status_code >= 400:
        raise SystemExit(f"simulate {name} → {response.status_code} {response.text}")


async def to_delivered(client: httpx.AsyncClient, ada: Api, tunde: Api) -> dict:
    session = await ada.call("POST", "/v1/auth/session", json_body={"display_name": "Ada"})
    say("Ada signed in", session["user"]["wallet_address"])
    provider_session = await tunde.call("POST", "/v1/auth/session", json_body={"display_name": "Tunde"})
    say("Tunde signed in", (provider_session["provider"] or {}).get("display_name", "no provider row — run seed.py"))

    intent = await ada.call("POST", "/v1/intents",
                            json_body={"text": "Paint a 2-bedroom in Surulere under ₦180k this Saturday"})
    say("intent structured", json.dumps(intent["spec"], separators=(",", ":"))[:96])

    recommendations = await ada.call("GET", f"/v1/providers/recommendations?intent_id={intent['intent_id']}")
    ready = [item for item in recommendations["items"] if item["provider"]["ready"]]
    if not ready:
        raise SystemExit("no provider has a wallet yet: run scripts/seed.py, then sign Tunde in")
    choice = ready[0]
    say("provider chosen", f"{choice['provider']['display_name']} · trust {choice['trust']['score']} · "
                           f"₦{choice['price']['amount_minor'] // 100:,}")

    created = await ada.call("POST", "/v1/transactions",
                             json_body={"intent_id": intent["intent_id"], "quote_id": choice["quote_id"]})
    tx_id = created["transaction"]["id"]
    signature = sign(created["authorization_typed_data"], ADA)
    await ada.call("POST", f"/v1/transactions/{tx_id}/authorize",
                   json_body={"signature": signature, "idkit_result": proof()}, idempotent=True)
    say("authorised", "signature + Selfie Check verified, policy ALLOW")

    # Phase one: the escrow assigns the id.
    first = await ada.call("POST", f"/v1/transactions/{tx_id}/fund", json_body={}, idempotent=True)
    assert first["step"] == "create_intent", first
    provider_address, token_address, amount = first["calls"][0]["args"]
    create_hash = hash32()
    await ada.call("POST", f"/v1/transactions/{tx_id}/fund", json_body={"tx_hash": create_hash}, idempotent=True)
    intent_id = random.randrange(1, 1_000_000)
    await simulate(client, "IntentCreated", intent_id, {"customer": ADA.address.lower(), "provider": provider_address.lower(),
                                                        "token": token_address.lower(), "amount": int(amount)},
                   tx_hash=create_hash)
    say("intent created on Arc", f"intentId {intent_id}")

    # Phase two: approve and fund.
    second = await ada.call("POST", f"/v1/transactions/{tx_id}/fund", json_body={}, idempotent=True)
    assert second["step"] == "fund_intent", second
    await simulate(client, "IntentFunded", intent_id, {"amount": int(amount)})
    say("funded on Arc", f"{int(amount) / 1e6:.2f} USDC in escrow")

    await tunde.call("POST", f"/v1/transactions/{tx_id}/start")
    for index, room in enumerate(("bedroom_1", "bedroom_2")):
        uploaded = await tunde.call("POST", f"/v1/transactions/{tx_id}/evidence",
                                    files={"file": (f"{room}.jpg", photo((40 + 60 * index, 90, 70)), "image/jpeg")},
                                    data={"kind": "AFTER_PHOTO", "scope_item": room, "caption": f"{room}, second coat"})
        say(f"evidence {room}", uploaded["evidence"]["sha256"][:18] + "… hashed and recorded")

    delivered = await tunde.call("POST", f"/v1/transactions/{tx_id}/deliver", json_body={}, idempotent=True)
    say("delivered", f"deliverable {delivered['deliverable_hash'][:18]}… · state {delivered['transaction']['state']}")
    return {"tx_id": tx_id, "intent_id": intent_id, "amount": int(amount)}


async def happy_path(client: httpx.AsyncClient, ada: Api, tunde: Api) -> None:
    print("\nHAPPY PATH")
    job = await to_delivered(client, ada, tunde)
    request = await ada.call("POST", f"/v1/transactions/{job['tx_id']}/release", json_body={}, idempotent=True)
    signature = sign(request["resolution_typed_data"], ADA)
    await ada.call("POST", f"/v1/transactions/{job['tx_id']}/release", json_body={"signature": signature}, idempotent=True)
    say("release signed", "customer signature + arbitrator co-signature")
    await simulate(client, "IntentResolved", job["intent_id"], {"customerAmount": 0, "providerAmount": job["amount"]})
    view = await ada.call("GET", f"/v1/transactions/{job['tx_id']}")
    timeline = await ada.call("GET", f"/v1/transactions/{job['tx_id']}/timeline")
    say("released", f"state {view['state']} · audit chain verified: {timeline['verification']['verified']}")
    assert view["state"] == "RELEASED", view["state"]


async def dispute_path(client: httpx.AsyncClient, ada: Api, tunde: Api) -> None:
    print("\nDISPUTE PATH")
    job = await to_delivered(client, ada, tunde)
    tx_id, intent_id = job["tx_id"], job["intent_id"]

    complaint_photo = await ada.call("POST", f"/v1/transactions/{tx_id}/evidence",
                                     files={"file": ("complaint.jpg", photo((190, 40, 40)), "image/jpeg")},
                                     data={"kind": "COMPLAINT", "caption": "Second bedroom, one coat"})
    complaint = await ada.call("POST", f"/v1/transactions/{tx_id}/complaint", idempotent=True,
                               json_body={"category": "INCOMPLETE", "text": "The second bedroom only got one coat",
                                          "evidence_ids": [complaint_photo["evidence"]["id"]], "idkit_result": proof()})
    await simulate(client, "DisputeRaised", intent_id, {"raisedBy": ADA.address.lower()})
    dispute_id = complaint["dispute"]["id"]
    say("complaint filed", "money frozen on-chain by the customer's own wallet")

    await tunde.call("POST", f"/v1/transactions/{tx_id}/evidence",
                     files={"file": ("counter.jpg", photo((60, 120, 200)), "image/jpeg")},
                     data={"kind": "COUNTER", "caption": "Both rooms, two coats"})
    await tunde.call("POST", f"/v1/disputes/{dispute_id}/respond",
                     json_body={"text": "I applied two coats in both rooms and photographed each one."})

    proposal = {}
    for _ in range(40):
        proposal = await ada.call("GET", f"/v1/disputes/{dispute_id}/proposal")
        if proposal.get("proposal_id"):
            break
        await asyncio.sleep(0.25)
    if not proposal.get("proposal_id"):
        raise SystemExit(f"no proposal: {proposal}")
    say("proposal", f"{proposal['remedy']} · {proposal['provider_bps']} bps · confidence {proposal['confidence']}")
    say("split", f"provider {proposal['split']['to_provider_minor'] / 1e6:.2f} USDC · "
                 f"customer {proposal['split']['to_customer_minor'] / 1e6:.2f} USDC")

    for api, account in ((ada, ADA), (tunde, TUNDE)):
        answer = await api.call("POST", f"/v1/disputes/{dispute_id}/accept",
                                json_body={"signature": sign(proposal["resolution_typed_data"], account)}, idempotent=True)
    say("both signed", f"{answer['status']} · two human signatures, the arbitrator only relays")

    await simulate(client, "IntentResolved", intent_id, {"customerAmount": proposal["split"]["to_customer_minor"],
                                                         "providerAmount": proposal["split"]["to_provider_minor"]})
    view = await ada.call("GET", f"/v1/transactions/{tx_id}")
    timeline = await ada.call("GET", f"/v1/transactions/{tx_id}/timeline")
    say("settled", f"state {view['state']} · audit chain verified: {timeline['verification']['verified']}")
    assert view["state"] == "SETTLED", view["state"]


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", choices=["happy", "dispute", "both"], default="both")
    parser.add_argument("--times", type=int, default=1, help="run the whole thing more than once (the PRD asks for twice)")
    args = parser.parse_args()
    async with httpx.AsyncClient(timeout=30) as client:
        health = (await client.get(BASE + "/healthz")).json()
        print(f"API {BASE} · db {health.get('db')} · rpc {health.get('rpc')} · leader {health.get('leader')}")
        ada, tunde = Api(client, ADA_TOKEN), Api(client, TUNDE_TOKEN)
        for run in range(1, args.times + 1):
            if args.times > 1:
                print(f"\n=== run {run} of {args.times} ===")
            if args.path in ("happy", "both"):
                await happy_path(client, ada, tunde)
            if args.path in ("dispute", "both"):
                await dispute_path(client, ada, tunde)
    print("\ndone.")


if __name__ == "__main__":
    asyncio.run(main())
