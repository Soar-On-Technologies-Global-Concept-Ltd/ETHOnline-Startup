"""One instance runs the workers. A Postgres advisory lock decides which, so a rolling deploy never doubles them up."""
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.db import get_engine
from app.core.logging import log

logger = logging.getLogger("leader")
LOCK_KEY = 728_431_001      # any constant; shared by every Intentra API instance


class Leadership:
    def __init__(self) -> None:
        self.connection: AsyncConnection | None = None

    @property
    def held(self) -> bool:
        return self.connection is not None

    async def acquire(self) -> bool:
        if self.held:
            return True
        connection = await get_engine().connect()
        got = bool((await connection.exec_driver_sql(f"SELECT pg_try_advisory_lock({LOCK_KEY})")).scalar())
        if not got:
            await connection.close()
            return False
        self.connection = connection
        log(logger, "workers leader acquired", key=LOCK_KEY)
        return True

    async def release(self) -> None:
        if self.connection is None:
            return
        try:
            await self.connection.exec_driver_sql(f"SELECT pg_advisory_unlock({LOCK_KEY})")
        finally:
            await self.connection.close()
            self.connection = None
            log(logger, "workers leader released", key=LOCK_KEY)
