"""The resolver's sender must never be stopped by a row it does not recognise. Marked `db`."""
import pytest
from sqlmodel import SQLModel, select

from app.core.db import dispose_engine, get_engine, session_scope, sessionmaker
from app.domains.payments import outbox
from app.domains.payments.models import ChainTx

pytestmark = pytest.mark.db


@pytest.fixture
async def db():
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        await conn.exec_driver_sql("TRUNCATE chain_txs RESTART IDENTITY CASCADE")
    yield
    await dispose_engine()


async def test_a_retired_kind_fails_its_own_row_and_lets_the_sender_carry_on(db):
    """ANCHOR, OPEN_DISPUTE and RESOLVE went with the old escrow; rows queued before the change must not wedge it."""
    async with session_scope() as s:
        s.add(ChainTx(kind="ANCHOR", args={"tx_key": "0x" + "11" * 32, "evidence_hash": "0x" + "22" * 32}))
    assert await outbox.send_next() == [], "the row was handled, not raised on"
    async with sessionmaker()() as s:
        row = (await s.exec(select(ChainTx))).one()
        assert row.status == "FAILED"
        assert "not a call this backend makes any more" in row.error


async def test_an_empty_queue_reports_that_there_is_nothing_to_do(db):
    assert await outbox.send_next() is None
