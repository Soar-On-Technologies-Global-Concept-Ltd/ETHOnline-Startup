"""The per-transaction hash chain that answers "why did the money go there?" (FR-20)."""
import uuid

from sqlalchemy import BigInteger, Column, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.columns import jsonb


class AuditEvent(SQLModel, table=True):
    __tablename__ = "audit_events"
    __table_args__ = (UniqueConstraint("transaction_id", "seq", name="ux_audit_seq"),)
    id: int | None = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    transaction_id: uuid.UUID = Field(foreign_key="transactions.id", index=True)
    seq: int
    actor: str = Field(max_length=80)
    event: str = Field(max_length=40)
    from_state: str = Field(max_length=32)
    to_state: str = Field(max_length=32)
    payload: dict = Field(sa_column=jsonb(False))
    prev_hash: str = Field(max_length=66)
    hash: str = Field(max_length=66)
    created_at: str = Field(max_length=40)
