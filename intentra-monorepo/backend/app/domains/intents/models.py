"""What the customer asked for, and the priced offers that answer it."""
import uuid
from datetime import datetime

from sqlalchemy import Column, Text, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.columns import big, jsonb, tstz, utcnow


class Intent(SQLModel, table=True):
    __tablename__ = "intents"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    customer_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    raw_text: str = Field(sa_column=Column(Text, nullable=False))
    structured: dict | None = Field(default=None, sa_column=jsonb())
    clarifying_question: str | None = Field(default=None, sa_column=Column(Text))
    status: str = Field(max_length=24)
    ai_model: str | None = Field(default=None, max_length=64)
    prompt_version: str | None = Field(default=None, max_length=32)
    created_at: datetime = Field(default_factory=utcnow, sa_column=tstz(False))


class Quote(SQLModel, table=True):
    __tablename__ = "quotes"
    __table_args__ = (UniqueConstraint("intent_id", "provider_id", "version", name="ux_quotes_version"),)
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    intent_id: uuid.UUID = Field(foreign_key="intents.id", index=True)
    provider_id: uuid.UUID = Field(foreign_key="providers.id")
    amount_minor: int = Field(sa_column=big(False))
    currency: str = Field(default="NGN", max_length=3)
    scope: dict = Field(sa_column=jsonb(False))
    scope_hash: str = Field(max_length=66)
    version: int = Field(default=1)
    rank: int = Field(default=0)
    why: str | None = Field(default=None, sa_column=Column(Text))
    trade_offs: str | None = Field(default=None, sa_column=Column(Text))
    trust_snapshot: dict | None = Field(default=None, sa_column=jsonb())
    expires_at: datetime = Field(sa_column=tstz(False))
    created_at: datetime = Field(default_factory=utcnow, sa_column=tstz(False))
