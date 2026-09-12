"""The provider side of the marketplace: trade, areas, rate and whether they are verified."""
import uuid
from datetime import date, datetime

from sqlalchemy import Index, Column, Date, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlmodel import Field, SQLModel

from app.core.columns import big, tstz, utcnow


class Provider(SQLModel, table=True):
    __tablename__ = "providers"
    __table_args__ = (Index("ix_providers_areas", "areas", postgresql_using="gin"),)
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID | None = Field(default=None, foreign_key="users.id", unique=True)
    email: str | None = Field(default=None, sa_column=Column(String(320), unique=True, nullable=True))
    display_name: str = Field(max_length=80)
    trade: str = Field(max_length=40, index=True)
    areas: list[str] = Field(default_factory=list, sa_column=Column(ARRAY(Text), nullable=False, server_default="{}"))
    base_rate_minor: int = Field(sa_column=big(False))
    currency: str = Field(default="NGN", max_length=3)
    verified: bool = Field(default=False)
    available_dates: list[date] = Field(default_factory=list, sa_column=Column(ARRAY(Date), nullable=False, server_default="{}"))
    seeded: bool = Field(default=False)
    created_at: datetime = Field(default_factory=utcnow, sa_column=tstz(False))
