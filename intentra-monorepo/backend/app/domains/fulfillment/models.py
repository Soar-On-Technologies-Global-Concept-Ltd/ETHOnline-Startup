"""The work itself: the checklist, what it covers and the deliverable that was submitted."""
import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from app.core.columns import jsonb, tstz, utcnow


class Fulfillment(SQLModel, table=True):
    __tablename__ = "fulfillments"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    transaction_id: uuid.UUID = Field(foreign_key="transactions.id", unique=True)
    status: str = Field(default="NOT_STARTED", max_length=16)
    checklist: dict = Field(sa_column=jsonb(False))
    coverage: dict | None = Field(default=None, sa_column=jsonb())
    started_at: datetime | None = Field(default=None, sa_column=tstz())
    deliverable_hash: str | None = Field(default=None, max_length=66)
    submit_tx: str | None = Field(default=None, max_length=66)
    delivered_at: datetime | None = Field(default=None, sa_column=tstz())
    updated_at: datetime = Field(default_factory=utcnow, sa_column=tstz(False))
