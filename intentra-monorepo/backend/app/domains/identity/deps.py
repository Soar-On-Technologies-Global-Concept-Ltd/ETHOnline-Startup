"""Who is calling: the verified Privy identity behind a request."""
import uuid
from dataclasses import dataclass

from fastapi import Header
from sqlmodel import select

from app.core.config import get_settings
from app.core.db import sessionmaker
from app.core.errors import Unauthorized
from app.core.logging import user_id_var
from app.domains.identity.models import User
from app.domains.providers import service as providers
from app.integrations import privy
from app.integrations.privy import PrivyIdentity  # re-exported so routers never import the adapter


@dataclass(frozen=True)
class CurrentUser:
    id: uuid.UUID
    did: str
    role: str
    wallet_address: str | None
    display_name: str | None
    provider_id: uuid.UUID | None


def bearer(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise Unauthorized("missing bearer token")
    return authorization[7:].strip()


async def privy_identity(authorization: str | None = Header(default=None)) -> PrivyIdentity:
    return await privy.authenticate(bearer(authorization))


async def current_user(authorization: str | None = Header(default=None)) -> CurrentUser:
    token = bearer(authorization)
    did = privy._fake(token).did if get_settings().privy_mode == "fake" else privy.verify_access_token(token)
    async with sessionmaker()() as s:
        user = (await s.exec(select(User).where(User.privy_did == did))).one_or_none()
        if user is None:
            raise Unauthorized("no session yet: call POST /v1/auth/session first", code="session_required")
        provider = await providers.for_user(s, user.id)
    user_id_var.set(str(user.id))
    return CurrentUser(user.id, user.privy_did, user.role, user.wallet_address, user.display_name, provider.id if provider else None)
