"""Who is acting. Every other domain asks here rather than reading the users or human_checks tables."""
import uuid

from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.columns import utcnow
from app.core.errors import Forbidden, NotFound
from app.domains.identity.models import HumanCheck, User
from app.integrations import world
from app.integrations.privy import PrivyIdentity
from app.integrations.world import VerifiedHuman


async def get(s: AsyncSession, user_id: uuid.UUID) -> User:
    user = await s.get(User, user_id)
    if user is None:
        raise NotFound("user not found")
    return user


async def get_optional(s: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await s.get(User, user_id)


async def by_did(s: AsyncSession, did: str) -> User | None:
    return (await s.exec(select(User).where(User.privy_did == did))).one_or_none()


async def wallet_of(s: AsyncSession, user_id: uuid.UUID | None) -> str | None:
    if user_id is None:
        return None
    user = await s.get(User, user_id)
    return user.wallet_address if user else None


async def wallets_for(s: AsyncSession, user_ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
    """One query for a page of providers, so recommendations do not fan out."""
    if not user_ids:
        return {}
    rows = (await s.exec(select(User.id, User.wallet_address).where(User.id.in_(list(user_ids))))).all()
    return {user_id: address for user_id, address in rows if address}


async def display_name_of(s: AsyncSession, user_id: uuid.UUID) -> str | None:
    user = await s.get(User, user_id)
    return user.display_name if user else None


async def mark_wallet_verified(s: AsyncSession, user_id: uuid.UUID) -> None:
    """Set the first time a signature recovers to the wallet Privy reported."""
    user = await s.get(User, user_id)
    if user is not None and user.wallet_verified_at is None:
        user.wallet_verified_at = utcnow()
        s.add(user)


async def set_role(s: AsyncSession, user_id: uuid.UUID, role: str) -> None:
    user = await s.get(User, user_id)
    if user is not None and user.role != role:
        user.role = role
        s.add(user)


async def start_session(s: AsyncSession, identity: PrivyIdentity, display_name: str | None) -> User:
    """Upsert the person behind a verified Privy token. A seeded account is claimed the first time its owner signs in."""
    user = await by_did(s, identity.did)
    if user is None and identity.email:
        seeded = (await s.exec(select(User).where(User.email == identity.email))).one_or_none()
        if seeded is not None and seeded.privy_did.startswith("seed:"):
            seeded.privy_did = identity.did
            user = seeded
    if user is None:
        user = User(privy_did=identity.did, email=identity.email, role="customer")
        s.add(user)
    if identity.email and user.email != identity.email:
        user.email = identity.email
    if identity.wallet_address and user.wallet_address != identity.wallet_address:
        user.wallet_address = identity.wallet_address.lower()
    if display_name:
        user.display_name = display_name
    s.add(user)
    await s.flush()
    return user


async def verify_human(idkit_result: dict, *, action: str, signal: str) -> VerifiedHuman:
    """Runs before the transaction row is locked: World verification is a network call."""
    return await world.verify(idkit_result, action=action, signal=signal)


def rp_context(action: str) -> dict:
    """The RP signature IDKit needs. Routers ask identity, never the adapter."""
    return world.rp_context(action)


async def record_human_check(s: AsyncSession, *, user_id: uuid.UUID, transaction_id: uuid.UUID | None, action: str,
                             verified: VerifiedHuman, scope_key: str) -> uuid.UUID:
    """A nullifier counts once per (action, transaction). A replay is refused rather than quietly accepted."""
    check = HumanCheck(user_id=user_id, transaction_id=transaction_id, action=action, nullifier=verified.nullifier,
                       signal_hash=verified.signal_hash, protocol_version=verified.protocol_version, scope_key=scope_key)
    try:
        async with s.begin_nested():
            s.add(check)
            await s.flush()
    except IntegrityError as err:
        raise Forbidden("this Selfie Check has already been used for this job", code="human_check_failed") from err
    return check.id
