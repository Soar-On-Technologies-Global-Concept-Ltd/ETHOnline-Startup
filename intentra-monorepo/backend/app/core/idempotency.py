"""Idempotency-Key handling (schematics §7.3): replay completed responses, wait on in-flight duplicates, reject key reuse."""
import hashlib
import uuid
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from fastapi.responses import JSONResponse
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.json import jsonable
from app.core.db import session_scope, sessionmaker
from app.core.hashing import canonical_json
from app.core.errors import Unprocessable
from app.core.columns import utcnow
from app.core.models import IdempotencyKey

P = TypeVar("P")


def request_hash(payload: Any) -> str:
    return hashlib.sha256(canonical_json(jsonable(payload))).hexdigest()


async def _completed(user_id: uuid.UUID, route: str, key: str, rhash: str) -> JSONResponse | None:
    async with sessionmaker()() as s:
        row = await s.get(IdempotencyKey, (user_id, route, key))
        if row is None:
            return None
        if row.request_hash != rhash:
            raise Unprocessable("Idempotency-Key reused with a different request", code="idempotency_key_reuse")
        if row.status == "COMPLETED":
            return JSONResponse(status_code=row.response_status or 200, content=row.response_body or {}, headers={"Idempotent-Replay": "true"})
        return None


async def _reserve(s: AsyncSession, user_id: uuid.UUID, route: str, key: str, rhash: str) -> JSONResponse | None:
    # A Core insert skips SQLModel's Python-side defaults, so created_at is set explicitly here.
    stmt = insert(IdempotencyKey).values(user_id=user_id, route=route, key=key, request_hash=rhash, status="IN_PROGRESS",
                                         created_at=utcnow()) \
        .on_conflict_do_nothing(index_elements=["user_id", "route", "key"]).returning(IdempotencyKey.key)
    inserted = (await s.exec(stmt)).first()
    if inserted is not None:
        return None
    row = (await s.exec(select(IdempotencyKey).where(IdempotencyKey.user_id == user_id, IdempotencyKey.route == route,
                                                    IdempotencyKey.key == key))).one()
    if row.request_hash != rhash:
        raise Unprocessable("Idempotency-Key reused with a different request", code="idempotency_key_reuse")
    return JSONResponse(status_code=row.response_status or 200, content=row.response_body or {}, headers={"Idempotent-Replay": "true"})


async def run(user_id: uuid.UUID, route: str, key: str | None, payload: Any,
              execute: Callable[[AsyncSession, P], Awaitable[tuple[int, dict]]],
              prepare: Callable[[], Awaitable[P]] | None = None) -> JSONResponse:
    rhash = request_hash(payload)
    if key:
        replay = await _completed(user_id, route, key, rhash)
        if replay is not None:
            return replay
    prepared = await prepare() if prepare else None
    async with session_scope() as s:
        if key:
            replay = await _reserve(s, user_id, route, key, rhash)
            if replay is not None:
                return replay
        status, body = await execute(s, prepared)
        body = jsonable(body)
        if key:
            row = await s.get(IdempotencyKey, (user_id, route, key))
            row.status, row.response_status, row.response_body = "COMPLETED", status, body
            s.add(row)
    return JSONResponse(status_code=status, content=body)
