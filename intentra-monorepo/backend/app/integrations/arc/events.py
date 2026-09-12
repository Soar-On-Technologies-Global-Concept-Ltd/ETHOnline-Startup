"""Decode IntentraEscrow logs into plain dicts."""
import inspect
from dataclasses import dataclass

from app.integrations.arc.abi import EVENT_NAMES
from app.integrations.arc.client import escrow


@dataclass(frozen=True)
class DecodedLog:
    name: str
    tx_hash: str
    log_index: int
    block_number: int
    contract: str
    tx_key: str
    args: dict


def _hex(value) -> str:
    if isinstance(value, (bytes, bytearray)):
        return "0x" + bytes(value).hex()
    value = str(value)
    return value if value.startswith("0x") else "0x" + value


_topics: dict[str, str] | None = None


def topics() -> dict[str, str]:
    global _topics
    if _topics is None:
        c = escrow()
        _topics = {_hex(getattr(c.events, n)().topic).lower(): n for n in EVENT_NAMES}
    return _topics


async def decode(log) -> DecodedLog | None:
    raw_topics = log.get("topics") or []
    if not raw_topics:
        return None
    name = topics().get(_hex(raw_topics[0]).lower())
    if name is None:
        return None
    event = getattr(escrow().events, name)().process_log(log)
    if inspect.isawaitable(event):
        event = await event
    args = {k: (_hex(v) if isinstance(v, (bytes, bytearray)) else (v.lower() if isinstance(v, str) and v.startswith("0x") else v))
            for k, v in dict(event["args"]).items()}
    return DecodedLog(name=name, tx_hash=_hex(log["transactionHash"]).lower(), log_index=int(log["logIndex"]),
                      block_number=int(log["blockNumber"]), contract=str(log["address"]).lower(), tx_key=args["txKey"].lower(), args=args)
