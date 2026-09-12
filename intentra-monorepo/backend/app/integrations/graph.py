"""TrustService data source: the intentra-arc subgraph on The Graph (live data only; no mocks)."""
import time
from dataclasses import dataclass

import httpx

from app.core.config import get_settings

QUERY = """
query ProviderTrust($ids: [Bytes!]) {
  providers(where: { id_in: $ids }) {
    id jobsFunded jobsReleased jobsSettled jobsRefunded disputes
    paidOutMicroUsdc refundedMicroUsdc secondsToEvidenceTotal evidenceAnchored
  }
  _meta { block { number } }
}
"""


@dataclass(frozen=True)
class ProviderStats:
    address: str
    funded: int = 0
    released: int = 0
    settled: int = 0
    refunded: int = 0
    disputes: int = 0
    paid_out_micro: int = 0
    refunded_micro: int = 0
    seconds_to_evidence_total: int = 0
    evidence_anchored: int = 0


META_QUERY = "query { _meta { block { number } } }"


@dataclass(frozen=True)
class GraphSnapshot:
    stats: dict[str, ProviderStats]
    block: int | None


_cache: dict[tuple, tuple[float, GraphSnapshot]] = {}


async def provider_stats(addresses: list[str]) -> GraphSnapshot | None:
    """Returns None when The Graph is not configured or unavailable; callers then show 'trust data unavailable'."""
    s = get_settings()
    ids = tuple(sorted({a.lower() for a in addresses if a}))
    if not s.graph_query_url or not ids:
        return None
    hit = _cache.get(ids)
    if hit and hit[0] > time.monotonic():
        return hit[1]
    headers = {"Content-Type": "application/json"}
    if s.graph_api_key:
        headers["Authorization"] = f"Bearer {s.graph_api_key.get_secret_value()}"
    try:
        async with httpx.AsyncClient(timeout=s.graph_timeout_seconds) as client:
            resp = await client.post(s.graph_query_url, json={"query": QUERY, "variables": {"ids": list(ids)}}, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    except (httpx.HTTPError, ValueError):
        return None
    if data.get("errors") or "data" not in data:
        return None
    stats = {}
    for p in data["data"].get("providers", []):
        stats[p["id"].lower()] = ProviderStats(
            address=p["id"].lower(), funded=int(p["jobsFunded"]), released=int(p["jobsReleased"]), settled=int(p["jobsSettled"]),
            refunded=int(p["jobsRefunded"]), disputes=int(p["disputes"]), paid_out_micro=int(p["paidOutMicroUsdc"]),
            refunded_micro=int(p["refundedMicroUsdc"]), seconds_to_evidence_total=int(p["secondsToEvidenceTotal"]),
            evidence_anchored=int(p["evidenceAnchored"]))
    block = ((data["data"].get("_meta") or {}).get("block") or {}).get("number")
    snap = GraphSnapshot(stats=stats, block=int(block) if block is not None else None)
    _cache[ids] = (time.monotonic() + 30, snap)
    return snap


async def head() -> int | None:
    """The subgraph's own block height, for the freshness check on /healthz."""
    s = get_settings()
    if not s.graph_query_url:
        return None
    headers = {"Content-Type": "application/json"}
    if s.graph_api_key:
        headers["Authorization"] = f"Bearer {s.graph_api_key.get_secret_value()}"
    try:
        async with httpx.AsyncClient(timeout=s.graph_timeout_seconds) as client:
            resp = await client.post(s.graph_query_url, json={"query": META_QUERY}, headers=headers)
        resp.raise_for_status()
        return int(resp.json()["data"]["_meta"]["block"]["number"])
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        return None
