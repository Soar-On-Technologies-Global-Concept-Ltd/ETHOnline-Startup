"""World Selfie Check: RP signatures (World's spec, EIP-191 over a 49/81-byte message) and server-side proof verification."""
import secrets
import time
from dataclasses import dataclass
from decimal import Decimal

import httpx
from eth_account import Account
from eth_account.messages import encode_defunct
from eth_utils import keccak

from app.core.config import get_settings
from app.core.errors import AppError, UpstreamVerificationFailed


class HumanCheckFailed(AppError):
    status, code = 403, "human_check_failed"


@dataclass(frozen=True)
class VerifiedHuman:
    nullifier: Decimal
    action: str
    protocol_version: str | None
    signal_hash: str | None
    raw: dict


def hash_to_field(data: bytes) -> bytes:
    return (int.from_bytes(keccak(data), "big") >> 8).to_bytes(32, "big")


def rp_message(nonce: bytes, created_at: int, expires_at: int, action: str | None) -> bytes:
    msg = bytes([0x01]) + nonce + created_at.to_bytes(8, "big") + expires_at.to_bytes(8, "big")
    if action is not None:
        msg += hash_to_field(action.encode("utf-8"))
    return msg


def sign_request(signing_key_hex: str, action: str | None, ttl: int = 300, *, now: int | None = None,
                 random_bytes: bytes | None = None) -> dict:
    key = bytes.fromhex(signing_key_hex[2:] if signing_key_hex.startswith("0x") else signing_key_hex)
    nonce = hash_to_field(random_bytes if random_bytes is not None else secrets.token_bytes(32))
    created = int(now if now is not None else time.time())
    expires = created + ttl
    signed = Account.sign_message(encode_defunct(primitive=rp_message(nonce, created, expires, action)), private_key=key)
    return {"sig": "0x" + bytes(signed.signature).hex(), "nonce": "0x" + nonce.hex(), "created_at": created, "expires_at": expires}


def rp_context(action: str) -> dict:
    s = get_settings()
    if s.world_mode == "fake":
        created = int(time.time())
        return {"mode": "fake", "rp_id": s.world_rp_id or "rp_test", "app_id": s.world_app_id or "app_test", "action": action,
                "nonce": "0x" + "00" * 32, "created_at": created, "expires_at": created + 300, "signature": "0x" + "00" * 65}
    if not s.world_rp_signing_key:
        raise AppError("World RP signing key is not configured", code="world_not_configured", status=500)
    sig = sign_request(s.world_rp_signing_key.get_secret_value(), action)
    return {"rp_id": s.world_rp_id, "app_id": s.world_app_id, "action": action, "nonce": sig["nonce"],
            "created_at": sig["created_at"], "expires_at": sig["expires_at"], "signature": sig["sig"]}


def _to_int(value: str | int) -> int:
    if isinstance(value, int):
        return value
    return int(value, 16) if str(value).startswith("0x") else int(value)


def _signal_hashes(signal: str) -> set[str]:
    variants = {signal.encode("utf-8")}
    if signal.startswith("0x"):
        variants.add(bytes.fromhex(signal[2:]))
    return {"0x" + hash_to_field(v).hex() for v in variants}


async def verify(idkit_result: dict, *, action: str, signal: str) -> VerifiedHuman:
    s = get_settings()
    if s.world_mode == "fake":
        if not idkit_result.get("fake") or not idkit_result.get("nullifier"):
            raise HumanCheckFailed("test proof missing")
        return VerifiedHuman(Decimal(_to_int(idkit_result["nullifier"])), action, "fake", None, idkit_result)
    if idkit_result.get("action") not in (None, action):
        raise HumanCheckFailed("proof was requested for a different action")
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(f"{s.world_verify_base_url.rstrip('/')}/api/v4/verify/{s.world_rp_id}", json=idkit_result)
    except httpx.HTTPError as err:
        raise UpstreamVerificationFailed("World verification is unavailable") from err
    body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
    if resp.status_code >= 500:
        raise UpstreamVerificationFailed("World verification is unavailable", details={"status": resp.status_code})
    if resp.status_code >= 400 or not body.get("success"):
        raise HumanCheckFailed("Selfie Check could not be verified", details={"world_code": body.get("code")})
    results = body.get("results") or []
    nullifier = body.get("nullifier") or next((r.get("nullifier") for r in results if r.get("nullifier")), None)
    if nullifier is None:
        raise HumanCheckFailed("verification returned no nullifier")
    signal_hash = next((r.get("signal_hash") for r in results if r.get("signal_hash")), None)
    if signal_hash and signal_hash not in ("0x0", "0x00") and signal_hash.lower() not in _signal_hashes(signal):
        raise HumanCheckFailed("proof is bound to a different transaction")
    return VerifiedHuman(Decimal(_to_int(nullifier)), body.get("action") or action, idkit_result.get("protocol_version"), signal_hash, body)
