"""GET /healthz — one line that says whether the demo can run."""
import os

from fastapi import APIRouter
from sqlalchemy import text

from app.core.db import sessionmaker
from app.domains.payments import service as payments
from app.orchestration import chain_events
from app.integrations import graph as graph_client

router = APIRouter(tags=["health"])


@router.get("/healthz", summary="Liveness and lag")
async def healthz() -> dict:
    from app.workers import runner

    out = {"version": os.getenv("GIT_SHA", "dev"), "db": "down", "rpc": "down", "leader": runner.is_leader(),
           "watcher_lag_blocks": None, "outbox": {}, "graph_lag_blocks": None}
    try:
        async with sessionmaker()() as s:
            await s.exec(text("SELECT 1"))
            out["db"], out["outbox"] = "ok", await payments.outbox_counts(s)
    except Exception as err:
        out["db_error"] = type(err).__name__
    try:
        head = await chain_events.head()
        if head is None:
            raise RuntimeError("no rpc")
        out["rpc"], out["head"] = "ok", head
        out["watcher_lag_blocks"] = await chain_events.lag_blocks()
        graph_head = await graph_client.head()
        out["graph_lag_blocks"] = None if graph_head is None else head - graph_head
    except Exception as err:
        out["rpc_error"] = type(err).__name__
    return out
