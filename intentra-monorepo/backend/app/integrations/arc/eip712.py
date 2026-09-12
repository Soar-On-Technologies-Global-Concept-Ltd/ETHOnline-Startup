"""EIP-712 Authorization and Resolution typed data (shared/eip712.json). The API builds typed data; clients only sign."""
from eth_account import Account
from eth_account.messages import encode_typed_data

from app.core.config import get_settings
from app.integrations.arc.client import checksum

DOMAIN_TYPE = [{"name": "name", "type": "string"}, {"name": "version", "type": "string"},
               {"name": "chainId", "type": "uint256"}, {"name": "verifyingContract", "type": "address"}]
AUTHORIZATION_TYPE = [{"name": "txKey", "type": "bytes32"}, {"name": "customer", "type": "address"},
                      {"name": "provider", "type": "address"}, {"name": "maxAmount", "type": "uint256"},
                      {"name": "scopeHash", "type": "bytes32"}, {"name": "expiresAt", "type": "uint64"}]
RESOLUTION_TYPE = [{"name": "txKey", "type": "bytes32"}, {"name": "providerBps", "type": "uint16"},
                   {"name": "outcomeHash", "type": "bytes32"}]


def domain() -> dict:
    s = get_settings()
    return {"name": "Intentra", "version": "1", "chainId": s.arc_chain_id, "verifyingContract": checksum(s.escrow_address)}


def authorization_typed_data(tx_key: str, customer: str, provider: str, max_amount: int, scope_hash: str, expires_at: int) -> dict:
    return {"types": {"EIP712Domain": DOMAIN_TYPE, "Authorization": AUTHORIZATION_TYPE}, "primaryType": "Authorization",
            "domain": domain(),
            "message": {"txKey": tx_key, "customer": checksum(customer), "provider": checksum(provider), "maxAmount": int(max_amount),
                        "scopeHash": scope_hash, "expiresAt": int(expires_at)}}


def resolution_typed_data(tx_key: str, provider_bps: int, outcome_hash: str) -> dict:
    return {"types": {"EIP712Domain": DOMAIN_TYPE, "Resolution": RESOLUTION_TYPE}, "primaryType": "Resolution", "domain": domain(),
            "message": {"txKey": tx_key, "providerBps": int(provider_bps), "outcomeHash": outcome_hash}}


def for_client(typed_data: dict) -> dict:
    """Large integers as strings so JavaScript never loses precision."""
    msg = {k: (str(v) if isinstance(v, int) and k in ("maxAmount",) else v) for k, v in typed_data["message"].items()}
    return {**typed_data, "message": msg}


def recover(typed_data: dict, signature: str) -> str:
    return Account.recover_message(encode_typed_data(full_message=typed_data), signature=signature).lower()


def struct_hash(typed_data: dict) -> str:
    return "0x" + bytes(encode_typed_data(full_message=typed_data).body).hex()
