"""Platform tables. Not domain entities: request de-duplication and worker cursors."""
import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from app.core.columns import jsonb, tstz, utcnow


class IdempotencyKey(SQLModel, table=True):
    __tablename__ = "idempotency_keys"
    user_id: uuid.UUID = Field(foreign_key="users.id", primary_key=True)
    route: str = Field(primary_key=True, max_length=120)
    key: str = Field(primary_key=True, max_length=80)
    request_hash: str = Field(max_length=64)
    status: str = Field(max_length=16)
    response_status: int | None = Field(default=None)
    response_body: dict | None = Field(default=None, sa_column=jsonb())
    created_at: datetime = Field(default_factory=utcnow, sa_column=tstz(False))


class KvCursor(SQLModel, table=True):
    __tablename__ = "kv_cursors"
    key: str = Field(primary_key=True, max_length=40)
    value: str = Field(max_length=80)
    updated_at: datetime = Field(default_factory=utcnow, sa_column=tstz(False))
