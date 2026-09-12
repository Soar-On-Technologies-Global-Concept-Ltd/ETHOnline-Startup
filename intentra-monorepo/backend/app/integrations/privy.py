"""Privy: verify access tokens (ES256) and read the embedded wallet server-side. Never trust a wallet address sent by the client."""
import time
from dataclasses import dataclass

import httpx
import jwt

from app.core.config import get_settings
from app.core.errors import DependencyUnavailable, Unauthorized

PRIVY_API = "https://auth.privy.io/api/v1"
_cache: dict[str, tuple[float, "PrivyIdentity"]] = {}


@dataclass(frozen=True)
class PrivyIdentity:
    did: str
    email: str | None
    wallet_address: str | None


def _pem(value: str) -> str:
    return value.replace("\\n", "\n")


def verify_access_token(token: str) -> str:
    s = get_settings()
    if s.privy_mode == "fake":
        return _fake(token).did
    if not s.privy_verification_key or not s.privy_app_id:
        raise Unauthorized("Privy is not configured")
    try:
        claims = jwt.decode(token, _pem(s.privy_verification_key), algorithms=["ES256"], audience=s.privy_app_id,
                            issuer="privy.io", leeway=30)
    except jwt.PyJWTError as err:
        raise Unauthorized("invalid or expired access token") from err
    sub = claims.get("sub")
    if not sub:
        raise Unauthorized("token has no subject")
    return sub


def _fake(token: str) -> PrivyIdentity:
    """Dev/test only: tokens look like  test:<did>:<wallet>:<email>."""
    parts = token.split(":")
    if len(parts) < 3 or parts[0] != "test":
        raise Unauthorized("invalid test token")
    did = "did:privy:" + parts[1]
    wallet = parts[2].lower() if parts[2].startswith("0x") else None
    email = parts[3] if len(parts) > 3 and parts[3] else None
    return PrivyIdentity(did=did, email=email, wallet_address=wallet)


def _parse_user(did: str, data: dict) -> PrivyIdentity:
    email, wallet = None, None
    for acct in data.get("linked_accounts", []):
        kind = acct.get("type")
        if kind == "email" and not email:
            email = acct.get("address")
        if kind == "wallet" and (acct.get("chain_type") in (None, "ethereum")):
            client_type = acct.get("wallet_client_type") or acct.get("walletClientType")
            if client_type in (None, "privy") and not wallet:
                wallet = (acct.get("address") or "").lower() or None
    return PrivyIdentity(did=did, email=email, wallet_address=wallet)


async def fetch_identity(did: str) -> PrivyIdentity:
    s = get_settings()
    hit = _cache.get(did)
    if hit and hit[0] > time.monotonic():
        return hit[1]
    if not s.privy_app_secret:
        raise DependencyUnavailable("Privy app secret is not configured")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{PRIVY_API}/users/{did}", auth=(s.privy_app_id, s.privy_app_secret.get_secret_value()),
                                    headers={"privy-app-id": s.privy_app_id})
        resp.raise_for_status()
    except httpx.HTTPError as err:
        raise DependencyUnavailable("Privy user lookup failed") from err
    ident = _parse_user(did, resp.json())
    _cache[did] = (time.monotonic() + 60, ident)
    return ident


async def authenticate(token: str) -> PrivyIdentity:
    """Verify the token, then resolve email and embedded wallet from Privy's server API."""
    if get_settings().privy_mode == "fake":
        return _fake(token)
    did = verify_access_token(token)
    return await fetch_identity(did)
