"""JSON that is safe to hash and safe to store: no floats, and every value has one spelling."""
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any


def utc_iso(dt: datetime | None = None) -> str:
    return (dt or datetime.now(timezone.utc)).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def jsonable(value: Any) -> Any:
    """JSON-safe and hash-safe: no floats (stringified), UUIDs/decimals/datetimes as strings."""
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [jsonable(v) for v in value]
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, (uuid.UUID, Decimal)):
        return str(value)
    if isinstance(value, datetime):
        return utc_iso(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bytes):
        return "0x" + value.hex()
    return value
