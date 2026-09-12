"""Who is acting: the person behind a Privy account, and the Selfie Checks they have passed."""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Column, Numeric, String, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.columns import jsonb, tstz, utcnow


class User(SQLModel, table=True):
    __tablename__ = "users"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    privy_did: str = Field(sa_column=Column(String(128), unique=True, nullable=False, index=True))
    email: str | None = Field(default=None, sa_column=Column(String(320), unique=True, nullable=True))
    wallet_address: str | None = Field(default=None, sa_column=Column(String(42), unique=True, nullable=True))
    wallet_verified_at: datetime | None = Field(default=None, sa_column=tstz())
    role: str = Field(default="customer", max_length=16)
    display_name: str | None = Field(default=None, max_length=80)
    created_at: datetime = Field(default_factory=utcnow, sa_column=tstz(False))


class HumanCheck(SQLModel, table=True):
    __tablename__ = "human_checks"
    __table_args__ = (UniqueConstraint("action", "nullifier", "scope_key", name="ux_human_checks"),)
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id")
    transaction_id: uuid.UUID | None = Field(default=None, foreign_key="transactions.id")
    action: str = Field(max_length=40)
    credential: str = Field(default="selfie_check", max_length=24)
    nullifier: Decimal = Field(sa_column=Column(Numeric(78, 0), nullable=False))
    signal_hash: str | None = Field(default=None, max_length=66)
    protocol_version: str | None = Field(default=None, max_length=8)
    raw: dict | None = Field(default=None, sa_column=jsonb())
    scope_key: str = Field(max_length=64)
    verified_at: datetime = Field(default_factory=utcnow, sa_column=tstz(False))
