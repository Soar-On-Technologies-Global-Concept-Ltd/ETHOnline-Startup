"""Permission: the typed data the customer signed, and the limits it sets."""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.columns import big, jsonb, tstz, utcnow


class Authorization(SQLModel, table=True):
    __tablename__ = "authorizations"
    __table_args__ = (UniqueConstraint("transaction_id", "version", name="ux_authorizations_version"),)
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    transaction_id: uuid.UUID = Field(foreign_key="transactions.id", index=True)
    version: int = Field(default=1)
    typed_data: dict = Field(sa_column=jsonb(False))
    signature: str = Field(sa_column=Column(Text, nullable=False))
    signer: str = Field(max_length=42)
    authorization_hash: str = Field(sa_column=Column(String(66), unique=True, nullable=False))
    max_amount_minor: int = Field(sa_column=big(False))
    scope_hash: str = Field(max_length=66)
    provider_address: str = Field(max_length=42)
    expires_at: datetime = Field(sa_column=tstz(False))
    human_check_id: uuid.UUID = Field(foreign_key="human_checks.id")
    policy_decision: dict = Field(sa_column=jsonb(False))
    created_at: datetime = Field(default_factory=utcnow, sa_column=tstz(False))
