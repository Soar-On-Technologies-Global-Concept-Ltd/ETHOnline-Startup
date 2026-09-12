"""TrustService: live on-chain history from The Graph, merged with clearly labelled seeded history."""
import uuid

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.states import PRE_FUNDING, TxState
from app.domains.providers import service as providers_service
from app.domains.providers.models import Provider
from app.domains.transactions.models import Transaction
from app.integrations.graph import provider_stats
from app.domains.providers.score import SeededHistory, TrustCard, compute

STALE_AFTER_BLOCKS = 50
DISPUTED_STATES = {TxState.DISPUTED.value, TxState.RESOLVING.value, TxState.PROPOSED.value, TxState.SETTLED.value, TxState.ESCALATED.value}
COMPLETED_STATES = {TxState.RELEASED.value, TxState.SETTLED.value}


async def seeded_history(s: AsyncSession, provider_ids: list[uuid.UUID]) -> dict[uuid.UUID, SeededHistory]:
    if not provider_ids:
        return {}
    rows = (await s.exec(select(Transaction.provider_id, Transaction.state)
                         .where(Transaction.seeded.is_(True), Transaction.provider_id.in_(provider_ids)))).all()
    counts: dict[uuid.UUID, list[int]] = {pid: [0, 0, 0] for pid in provider_ids}   # completed, disputes, funded
    pre_funding = {s_.value for s_ in PRE_FUNDING}
    for provider_id, state in rows:
        if provider_id is None or state in pre_funding:
            continue
        c = counts[provider_id]
        c[2] += 1
        c[0] += state in COMPLETED_STATES
        c[1] += state in DISPUTED_STATES
    return {pid: SeededHistory(completed=c[0], disputes=c[1], funded=c[2]) for pid, c in counts.items()}


async def chain_head() -> int | None:
    """Only used to tell whether the subgraph is behind; a missing RPC never blocks a recommendation."""
    try:
        from app.integrations.arc.client import w3
        return int(await w3().eth.block_number)
    except Exception:
        return None


async def cards(s: AsyncSession, providers: list[Provider], head: int | None = None) -> dict[uuid.UUID, TrustCard]:
    """One Graph query per request; providers with no wallet yet score on seeded history alone."""
    head = head if head is not None else await chain_head()
    addresses = await providers_service.wallets_for(s, providers)
    snapshot = await provider_stats(list(addresses.values()))
    seeded = await seeded_history(s, [p.id for p in providers])
    stale = snapshot is not None and head is not None and snapshot.block is not None \
        and head - snapshot.block > STALE_AFTER_BLOCKS
    out: dict[uuid.UUID, TrustCard] = {}
    for provider in providers:
        stats = None if snapshot is None else snapshot.stats.get((addresses.get(provider.id) or "").lower())
        card = compute(stats, seeded.get(provider.id, SeededHistory()), available=snapshot is not None and not stale)
        out[provider.id] = card
    return out


async def card_for(s: AsyncSession, provider: Provider, head: int | None = None) -> TrustCard:
    return (await cards(s, [provider], head))[provider.id]
