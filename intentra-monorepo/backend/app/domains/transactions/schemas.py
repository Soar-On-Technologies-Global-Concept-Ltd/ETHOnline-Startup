"""What the client sends to transaction routes."""
import uuid

from pydantic import BaseModel, Field


class SelectQuoteIn(BaseModel):
    intent_id: uuid.UUID
    quote_id: uuid.UUID


class CancelIn(BaseModel):
    reason: str | None = Field(default=None, max_length=40)
