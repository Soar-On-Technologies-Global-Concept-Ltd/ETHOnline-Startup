import pytest
from app.core.db import session_scope, sessionmaker
from app.domains.identity.models import User
from app.domains.providers import service as providers
from app.core.errors import Conflict
from sqlmodel import SQLModel
from app.core.db import get_engine, dispose_engine

pytestmark = pytest.mark.db

TABLES = ("audit_events, blockchain_events, resolution_acceptances, resolution_proposals, disputes, complaints, evidence, "
          "chain_txs, idempotency_keys, fulfillments, payments, authorizations, human_checks, transactions, quotes, "
          "intents, providers, users, kv_cursors")

@pytest.fixture
async def db():
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        await conn.exec_driver_sql(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE")
    yield
    await dispose_engine()

@pytest.fixture
async def unseeded_user(db):
    async with session_scope() as s:
        user = User(privy_did="did:privy:newguy", email="new@intentra.demo", display_name="New Guy", wallet_address="0x123")
        s.add(user)
        await s.flush()
        return user.id

async def test_onboard_new_provider(unseeded_user):
    async with session_scope() as s:
        provider = await providers.onboard_user(s, unseeded_user, "plumbing", ["Ikeja"], 5000000)
        assert provider.trade == "plumbing"
        assert provider.base_rate_minor == 5000000
        assert provider.areas == ["Ikeja"]
        assert not provider.verified
        assert not provider.seeded

    # Fetch it back
    async with sessionmaker()() as s:
        profile = await providers.for_user(s, unseeded_user)
        assert profile is not None
        assert profile.trade == "plumbing"

async def test_cannot_onboard_twice(unseeded_user):
    async with session_scope() as s:
        await providers.onboard_user(s, unseeded_user, "plumbing", ["Ikeja"], 5000000)
    
    with pytest.raises(Conflict):
        async with session_scope() as s:
            await providers.onboard_user(s, unseeded_user, "electrical", ["Ikeja"], 6000000)
