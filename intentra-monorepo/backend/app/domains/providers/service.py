"""Reading and linking providers. Every other domain asks here rather than reading the providers table."""
import uuid

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.errors import NotFound
from app.domains.identity import service as identity
from app.domains.providers.models import Provider


async def get(s: AsyncSession, provider_id: uuid.UUID) -> Provider:
    provider = await s.get(Provider, provider_id)
    if provider is None:
        raise NotFound("provider not found")
    return provider


async def get_optional(s: AsyncSession, provider_id: uuid.UUID | None) -> Provider | None:
    return None if provider_id is None else await s.get(Provider, provider_id)


async def list_all(s: AsyncSession) -> list[Provider]:
    return list((await s.exec(select(Provider).order_by(Provider.display_name))).all())


async def for_user(s: AsyncSession, user_id: uuid.UUID) -> Provider | None:
    return (await s.exec(select(Provider).where(Provider.user_id == user_id))).one_or_none()


async def claim_for_user(s: AsyncSession, user_id: uuid.UUID, email: str | None) -> Provider | None:
    """A seeded provider row is linked the first time its owner signs in with that email."""
    linked = await for_user(s, user_id)
    if linked is not None or not email:
        return linked
    unlinked = (await s.exec(select(Provider).where(Provider.email == email, Provider.user_id.is_(None)))).one_or_none()
    if unlinked is None:
        return None
    unlinked.user_id = user_id
    s.add(unlinked)
    await identity.set_role(s, user_id, "provider")
    return unlinked


async def summary(s: AsyncSession, provider_id: uuid.UUID | None) -> dict | None:
    provider = await get_optional(s, provider_id)
    if provider is None:
        return None
    return {"id": str(provider.id), "display_name": provider.display_name, "trade": provider.trade,
            "verified": provider.verified, "seeded": provider.seeded}


async def wallet_of(s: AsyncSession, provider_id: uuid.UUID | None) -> str | None:
    """The address the escrow will pay. None means the provider has not activated a wallet yet."""
    provider = await get_optional(s, provider_id)
    return None if provider is None else await identity.wallet_of(s, provider.user_id)


async def wallets_for(s: AsyncSession, providers: list[Provider]) -> dict[uuid.UUID, str]:
    by_user = await identity.wallets_for(s, [p.user_id for p in providers if p.user_id])
    return {p.id: by_user[p.user_id] for p in providers if p.user_id in by_user}


async def is_verified(s: AsyncSession, provider_id: uuid.UUID | None) -> bool:
    provider = await get_optional(s, provider_id)
    return bool(provider and provider.verified)
