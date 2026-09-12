"""Proof of what was delivered: hashed, stored privately and anchored on Arc."""
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Column, Text, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.columns import tstz, utcnow


class Evidence(SQLModel, table=True):
    __tablename__ = "evidence"
    __table_args__ = (UniqueConstraint("transaction_id", "sha256", name="ux_evidence_hash"),)
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    transaction_id: uuid.UUID = Field(foreign_key="transactions.id", index=True)
    submitted_by: uuid.UUID = Field(foreign_key="users.id")
    role: str = Field(max_length=16)
    kind: str = Field(max_length=16)
    scope_item: str | None = Field(default=None, max_length=40)
    sha256: str = Field(max_length=66)
    storage_uri: str = Field(sa_column=Column(Text, nullable=False))
    mime: str = Field(max_length=32)
    bytes: int = Field(default=0)
    caption: str | None = Field(default=None, max_length=280)
    anchor_tx_id: int | None = Field(default=None, sa_column=Column(BigInteger, nullable=True))
    anchored_tx: str | None = Field(default=None, max_length=66)
    created_at: datetime = Field(default_factory=utcnow, sa_column=tstz(False))
