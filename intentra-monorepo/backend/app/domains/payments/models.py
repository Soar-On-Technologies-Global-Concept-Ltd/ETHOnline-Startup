"""Money and the chain: payment records, resolver transactions and the escrow logs seen so far."""
import uuid
from datetime import datetime

from sqlalchemy import Index, text, BigInteger, Column, String, Text, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.columns import big, jsonb, tstz, utcnow


class Payment(SQLModel, table=True):
    __tablename__ = "payments"
    __table_args__ = (UniqueConstraint("rail", "direction", "external_ref", name="ux_payments_ref"),)
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    transaction_id: uuid.UUID = Field(foreign_key="transactions.id", index=True)
    rail: str = Field(default="arc", max_length=8)
    direction: str = Field(max_length=16)
    external_ref: str = Field(max_length=96)
    status: str = Field(max_length=16)
    amount_minor: int | None = Field(default=None, sa_column=big())
    raw: dict | None = Field(default=None, sa_column=jsonb())
    created_at: datetime = Field(default_factory=utcnow, sa_column=tstz(False))
    updated_at: datetime = Field(default_factory=utcnow, sa_column=tstz(False))


class ChainTx(SQLModel, table=True):
    __tablename__ = "chain_txs"
    __table_args__ = (Index("ix_outbox_queue", "status", "id",
                             postgresql_where=text("status IN ('QUEUED', 'SENT')")),)
    id: int | None = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    transaction_id: uuid.UUID | None = Field(default=None, foreign_key="transactions.id", index=True)
    kind: str = Field(max_length=24)
    args: dict = Field(sa_column=jsonb(False))
    status: str = Field(default="QUEUED", max_length=12, index=True)
    nonce: int | None = Field(default=None, sa_column=big())
    tx_hash: str | None = Field(default=None, sa_column=Column(String(66), unique=True, nullable=True))
    error: str | None = Field(default=None, sa_column=Column(Text))
    attempts: int = Field(default=0)
    created_at: datetime = Field(default_factory=utcnow, sa_column=tstz(False))
    sent_at: datetime | None = Field(default=None, sa_column=tstz())
    mined_at: datetime | None = Field(default=None, sa_column=tstz())


class BlockchainEvent(SQLModel, table=True):
    __tablename__ = "blockchain_events"
    tx_hash: str = Field(primary_key=True, max_length=66)
    log_index: int = Field(primary_key=True)
    block_number: int = Field(sa_column=big(False))
    contract: str = Field(max_length=42)
    name: str = Field(max_length=32)
    tx_key: str | None = Field(default=None, max_length=66, index=True)
    payload: dict = Field(sa_column=jsonb(False))
    handled: bool = Field(default=False)
    handle_error: str | None = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=utcnow, sa_column=tstz(False))
