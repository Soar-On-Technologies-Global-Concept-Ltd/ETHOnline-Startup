"""The only place hashes are computed. keccak256 for anything that goes on-chain or into EIP-712; SHA-256 for files and the audit chain."""
import hashlib
import json
from typing import Any

from eth_utils import keccak

ZERO_HASH = "0x" + "00" * 32


def _reject_floats(obj: Any) -> None:
    if isinstance(obj, float):
        raise TypeError("floats are not allowed in hashed payloads")
    if isinstance(obj, dict):
        for v in obj.values():
            _reject_floats(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _reject_floats(v)


def canonical_json(obj: Any) -> bytes:
    _reject_floats(obj)
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def keccak_hex(data: bytes) -> str:
    return "0x" + keccak(data).hex()


def sha256_hex(data: bytes) -> str:
    return "0x" + hashlib.sha256(data).hexdigest()


def hex_to_bytes(value: str) -> bytes:
    return bytes.fromhex(value[2:] if value.startswith("0x") else value)


def scope_hash(scope: dict) -> str:
    return keccak_hex(canonical_json(scope))


def deliverable_hash(after_photo_sha256s: list[str]) -> str:
    return keccak_hex(b"".join(hex_to_bytes(h) for h in sorted(h.lower() for h in after_photo_sha256s)))


def complaint_hash(tx_key: str, category: str, text: str, evidence_sha256s: list[str]) -> str:
    return keccak_hex(canonical_json({"tx_key": tx_key.lower(), "category": category, "text": text,
                                      "evidence": sorted(h.lower() for h in evidence_sha256s)}))


def outcome_hash(tx_key: str, proposal_id: str, remedy: str, provider_bps: int, cited_sha256s: list[str],
                 rationale: str, model: str | None, prompt_version: str | None) -> str:
    return keccak_hex(canonical_json({
        "tx_key": tx_key.lower(), "proposal_id": proposal_id, "remedy": remedy, "provider_bps": provider_bps,
        "cited": sorted(h.lower() for h in cited_sha256s), "rationale_sha256": sha256_hex(rationale.encode("utf-8")),
        "model": model or "", "prompt_version": prompt_version or "",
    }))


def audit_hash(prev_hash: str, row: dict) -> str:
    return sha256_hex(hex_to_bytes(prev_hash) + canonical_json(row))
