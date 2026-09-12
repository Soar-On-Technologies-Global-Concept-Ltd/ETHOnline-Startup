"""When the two sides disagree: the complaint, the dispute, the proposal and each signature on it."""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Column, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PG_UUID
from sqlmodel import Field, SQLModel

from app.core.columns import big, jsonb, tstz, utcnow


class Complaint(SQLModel, table=True):
    __tablename__ = "complaints"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    transaction_id: uuid.UUID = Field(foreign_key="transactions.id", index=True)
    filed_by: uuid.UUID = Field(foreign_key="users.id")
    category: str = Field(max_length=16)
    text: str = Field(sa_column=Column(Text, nullable=False))
    evidence_ids: list[uuid.UUID] = Field(default_factory=list, sa_column=Column(ARRAY(PG_UUID(as_uuid=True)), nullable=False))
    complaint_hash: str = Field(max_length=66)
    human_check_id: uuid.UUID = Field(foreign_key="human_checks.id")
    created_at: datetime = Field(default_factory=utcnow, sa_column=tstz(False))


class Dispute(SQLModel, table=True):
    __tablename__ = "disputes"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    transaction_id: uuid.UUID = Field(foreign_key="transactions.id", unique=True)
    complaint_id: uuid.UUID = Field(foreign_key="complaints.id", unique=True)
    level: str = Field(default="L1", max_length=4)
    status: str = Field(default="OPENING", max_length=20)
    response_text: str | None = Field(default=None, sa_column=Column(Text))
    response_deadline: datetime | None = Field(default=None, sa_column=tstz())
    created_at: datetime = Field(default_factory=utcnow, sa_column=tstz(False))
    updated_at: datetime = Field(default_factory=utcnow, sa_column=tstz(False))


class ResolutionProposal(SQLModel, table=True):
    __tablename__ = "resolution_proposals"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    dispute_id: uuid.UUID = Field(foreign_key="disputes.id", unique=True)
    level: str = Field(max_length=4)
    remedy: str = Field(max_length=16)
    provider_bps: int
    to_provider_minor: int = Field(sa_column=big(False))
    to_customer_minor: int = Field(sa_column=big(False))
    rationale: str = Field(sa_column=Column(Text, nullable=False))
    cited_evidence_ids: list[uuid.UUID] = Field(default_factory=list, sa_column=Column(ARRAY(PG_UUID(as_uuid=True)), nullable=False))
    model: str | None = Field(default=None, max_length=64)
    prompt_version: str | None = Field(default=None, max_length=32)
    input_hash: str | None = Field(default=None, max_length=66)
    confidence: Decimal | None = Field(default=None, sa_column=Column(Numeric(3, 2)))
    outcome_hash: str = Field(sa_column=Column(String(66), unique=True, nullable=False))
    accept_deadline: datetime = Field(sa_column=tstz(False))
    status: str = Field(default="OPEN", max_length=12)
    created_at: datetime = Field(default_factory=utcnow, sa_column=tstz(False))


class ResolutionAcceptance(SQLModel, table=True):
    __tablename__ = "resolution_acceptances"
    __table_args__ = (UniqueConstraint("proposal_id", "user_id", name="ux_acceptance"),)
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    proposal_id: uuid.UUID = Field(foreign_key="resolution_proposals.id", index=True)
    user_id: uuid.UUID = Field(foreign_key="users.id")
    role: str = Field(max_length=16)
    decision: str = Field(max_length=8)
    signature: str | None = Field(default=None, sa_column=Column(Text))
    typed_data: dict | None = Field(default=None, sa_column=jsonb())
    created_at: datetime = Field(default_factory=utcnow, sa_column=tstz(False))
