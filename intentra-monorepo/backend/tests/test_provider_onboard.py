import pytest
from app.core.db import session_scope, sessionmaker
from app.domains.identity.models import User
from app.domains.providers import service as providers
from app.core.errors import Conflict

pytestmark = pytest.mark.db

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
