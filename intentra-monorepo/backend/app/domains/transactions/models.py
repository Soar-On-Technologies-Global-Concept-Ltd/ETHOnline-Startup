"""The aggregate root. Everything else in the system hangs off one transaction."""
import uuid
from datetime import datetime

from sqlalchemy import Index, Column, String
from sqlmodel import Field, SQLModel

from app.core.columns import big, jsonb, tstz, utcnow


class Transaction(SQLModel, table=True):
    __tablename__ = "transactions"
    __table_args__ = (Index("ix_tx_state_release", "state", "release_after"),)
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tx_key: str = Field(sa_column=Column(String(66), unique=True, nullable=False))
    intent_id: uuid.UUID = Field(foreign_key="intents.id", unique=True)
    quote_id: uuid.UUID | None = Field(default=None, foreign_key="quotes.id")
    customer_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    provider_id: uuid.UUID | None = Field(default=None, foreign_key="providers.id", index=True)
    state: str = Field(max_length=32, index=True)
    version: int = Field(default=0)
    rail: str = Field(default="arc", max_length=8)
    amount_minor: int | None = Field(default=None, sa_column=big())
    currency: str = Field(default="USDC", max_length=8)
    display_amount_minor: int | None = Field(default=None, sa_column=big())
    fx_rate_ngn_per_usdc: int | None = Field(default=None)
    dispute_window_s: int | None = Field(default=None)
    authorization_offer: dict | None = Field(default=None, sa_column=jsonb())
    expires_at: datetime | None = Field(default=None, sa_column=tstz())
    release_after: datetime | None = Field(default=None, sa_column=tstz())
    funded_at: datetime | None = Field(default=None, sa_column=tstz())
    delivered_at: datetime | None = Field(default=None, sa_column=tstz())
    closed_at: datetime | None = Field(default=None, sa_column=tstz())
    close_reason: str | None = Field(default=None, max_length=40)
    seeded: bool = Field(default=False)
    created_at: datetime = Field(default_factory=utcnow, sa_column=tstz(False))
    updated_at: datetime = Field(default_factory=utcnow, sa_column=tstz(False))
