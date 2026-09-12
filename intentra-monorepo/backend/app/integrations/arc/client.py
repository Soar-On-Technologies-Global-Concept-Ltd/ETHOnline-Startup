"""Arc testnet access (chain 5042002). USDC ERC-20 interface uses 6 decimals; gas is paid in USDC."""
from functools import lru_cache

from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_utils import to_checksum_address
from web3 import AsyncHTTPProvider, AsyncWeb3

from app.core.config import get_settings
from app.integrations.arc.abi import ERC20_APPROVE_ABI, ESCROW_ABI


@lru_cache
def w3() -> AsyncWeb3:
    return AsyncWeb3(AsyncHTTPProvider(get_settings().arc_rpc_url, request_kwargs={"timeout": 10}))


def checksum(address: str) -> str:
    return to_checksum_address(address)


@lru_cache
def escrow():
    return w3().eth.contract(address=checksum(get_settings().escrow_address), abi=ESCROW_ABI)


@lru_cache
def usdc():
    return w3().eth.contract(address=checksum(get_settings().usdc_address), abi=ERC20_APPROVE_ABI)


def resolver() -> LocalAccount | None:
    key = get_settings().resolver_private_key
    return Account.from_key(key.get_secret_value()) if key else None


def explorer_tx(tx_hash: str | None) -> str | None:
    return (get_settings().explorer_tx_url + tx_hash) if tx_hash else None


def call(to: str, fn: str, args: list) -> dict:
    """Call description for the user's Privy wallet (the frontend encodes it with the shared ABI)."""
    return {"chain_id": get_settings().arc_chain_id, "to": checksum(to), "fn": fn, "args": args}
