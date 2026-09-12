"""The two typed-data structures the parties sign.

`ResolveIntent` is the contract's own type: `executeWithSignatures` recovers two distinct signers from
{customer, provider, aiArbitrator} against it, so the domain and field order here must match IntentraEscrow.sol
exactly — the contract builds its domain with `EIP712("IntentraEscrow", "1")`.

`Authorization` is Intentra's own mandate. The escrow never sees it: it is the record that a human approved this
job, this provider and this maximum, and it is what the policy engine and the audit trail check against.
"""
from eth_account import Account
from eth_account.messages import encode_typed_data

from app.core.config import get_settings
from app.integrations.arc.client import checksum

DOMAIN_TYPE = [{"name": "name", "type": "string"}, {"name": "version", "type": "string"},
               {"name": "chainId", "type": "uint256"}, {"name": "verifyingContract", "type": "address"}]
AUTHORIZATION_TYPE = [{"name": "txKey", "type": "bytes32"}, {"name": "customer", "type": "address"},
                      {"name": "provider", "type": "address"}, {"name": "maxAmount", "type": "uint256"},
                      {"name": "scopeHash", "type": "bytes32"}, {"name": "expiresAt", "type": "uint64"}]
RESOLVE_INTENT_TYPE = [{"name": "intentId", "type": "uint256"}, {"name": "customerAmount", "type": "uint256"},
                       {"name": "providerAmount", "type": "uint256"}]
BIG_FIELDS = ("maxAmount", "intentId", "customerAmount", "providerAmount")


def contract_domain() -> dict:
    """Must match EIP712("IntentraEscrow", "1") in the deployed contract."""
    s = get_settings()
    return {"name": "IntentraEscrow", "version": "1", "chainId": s.arc_chain_id,
            "verifyingContract": checksum(s.escrow_address)}


def mandate_domain() -> dict:
    """Intentra's own domain for the off-chain authorization: never presented to the contract."""
    s = get_settings()
    return {"name": "Intentra", "version": "1", "chainId": s.arc_chain_id,
            "verifyingContract": checksum(s.escrow_address)}


def authorization_typed_data(tx_key: str, customer: str, provider: str, max_amount: int, scope_hash: str,
                             expires_at: int) -> dict:
    return {"types": {"EIP712Domain": DOMAIN_TYPE, "Authorization": AUTHORIZATION_TYPE}, "primaryType": "Authorization",
            "domain": mandate_domain(),
            "message": {"txKey": tx_key, "customer": checksum(customer), "provider": checksum(provider),
                        "maxAmount": int(max_amount), "scopeHash": scope_hash, "expiresAt": int(expires_at)}}


def resolution_typed_data(intent_id: int, customer_amount: int, provider_amount: int) -> dict:
    """What both signers sign for executeWithSignatures. The amounts are exact micro-USDC and must sum to the escrow."""
    return {"types": {"EIP712Domain": DOMAIN_TYPE, "ResolveIntent": RESOLVE_INTENT_TYPE}, "primaryType": "ResolveIntent",
            "domain": contract_domain(),
            "message": {"intentId": int(intent_id), "customerAmount": int(customer_amount),
                        "providerAmount": int(provider_amount)}}


def for_client(typed_data: dict) -> dict:
    """Large integers as strings so JavaScript never loses precision."""
    message = {k: (str(v) if isinstance(v, int) and k in BIG_FIELDS else v) for k, v in typed_data["message"].items()}
    return {**typed_data, "message": message}


def recover(typed_data: dict, signature: str) -> str:
    return Account.recover_message(encode_typed_data(full_message=typed_data), signature=signature).lower()


def struct_hash(typed_data: dict) -> str:
    return "0x" + bytes(encode_typed_data(full_message=typed_data).body).hex()
