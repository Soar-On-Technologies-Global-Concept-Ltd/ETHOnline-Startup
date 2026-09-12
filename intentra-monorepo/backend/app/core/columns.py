"""Column helpers shared by every domain's tables. Money is integers, timestamps are timestamptz UTC, hashes are 0x-hex."""
from datetime import datetime, timezone

from sqlalchemy import BigInteger, Column, DateTime
from sqlalchemy.dialects.postgresql import JSONB


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def tstz(nullable: bool = True) -> Column:
    return Column(DateTime(timezone=True), nullable=nullable)


def jsonb(nullable: bool = True) -> Column:
    return Column(JSONB, nullable=nullable)


def big(nullable: bool = True) -> Column:
    return Column(BigInteger, nullable=nullable)
