"""Idempotency-Key behaviour against a real database (schematics §7.3). Marked `db`."""
import asyncio
import json
import uuid

import pytest
from sqlmodel import SQLModel, select

from app.core.db import dispose_engine, get_engine, sessionmaker
from app.core.errors import Unprocessable
from app.core.idempotency import run as idempotent
from app.core.models import IdempotencyKey
from app.domains.identity.models import User

pytestmark = pytest.mark.db


@pytest.fixture
async def user():
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    async with sessionmaker()() as s:
        row = User(privy_did=f"did:privy:{uuid.uuid4()}", email=f"{uuid.uuid4()}@intentra.demo")
        s.add(row)
        await s.commit()
    yield row
    await dispose_engine()


def counter():
    calls = []

    async def execute(session, _prepared):
        calls.append(1)
        return 201, {"created": len(calls), "id": str(uuid.uuid4())}

    return calls, execute


async def test_the_first_call_runs_and_is_recorded(user):
    calls, execute = counter()
    key = str(uuid.uuid4())
    response = await idempotent(user.id, "authorize", key, {"a": 1}, execute)
    assert response.status_code == 201 and len(calls) == 1
    async with sessionmaker()() as s:
        row = await s.get(IdempotencyKey, (user.id, "authorize", key))
        assert row.status == "COMPLETED" and row.response_status == 201 and row.created_at is not None


async def test_the_same_key_replays_the_stored_response(user):
    calls, execute = counter()
    key = str(uuid.uuid4())
    first = await idempotent(user.id, "authorize", key, {"a": 1}, execute)
    second = await idempotent(user.id, "authorize", key, {"a": 1}, execute)
    assert len(calls) == 1, "the work must not run twice"
    # The stored response comes back from a JSONB column, so keys can be in another order; the response is the same.
    assert json.loads(first.body) == json.loads(second.body)
    assert first.status_code == second.status_code
    assert second.headers.get("Idempotent-Replay") == "true"


async def test_the_same_key_with_a_different_body_is_refused(user):
    _, execute = counter()
    key = str(uuid.uuid4())
    await idempotent(user.id, "authorize", key, {"a": 1}, execute)
    with pytest.raises(Unprocessable) as err:
        await idempotent(user.id, "authorize", key, {"a": 2}, execute)
    assert err.value.code == "idempotency_key_reuse"


async def test_concurrent_duplicates_have_one_effect(user):
    calls, execute = counter()
    key = str(uuid.uuid4())
    responses = await asyncio.gather(*[idempotent(user.id, "fund", key, {"a": 1}, execute) for _ in range(4)])
    assert len(calls) == 1
    bodies = [json.loads(r.body) for r in responses]
    assert all(body == bodies[0] for body in bodies)
    assert {r.status_code for r in responses} == {201}


async def test_different_keys_do_different_work(user):
    calls, execute = counter()
    await idempotent(user.id, "fund", str(uuid.uuid4()), {"a": 1}, execute)
    await idempotent(user.id, "fund", str(uuid.uuid4()), {"a": 1}, execute)
    assert len(calls) == 2


async def test_verification_runs_before_the_lock_and_only_once(user):
    """prepare() is where World and signature checks live: a replay must not re-run them."""
    prepared = []

    async def prepare():
        prepared.append(1)
        return "verified"

    async def execute(session, value):
        assert value == "verified"
        return 200, {"ok": True}

    key = str(uuid.uuid4())
    await idempotent(user.id, "complaint", key, {"a": 1}, execute, prepare)
    await idempotent(user.id, "complaint", key, {"a": 1}, execute, prepare)
    assert len(prepared) == 1
