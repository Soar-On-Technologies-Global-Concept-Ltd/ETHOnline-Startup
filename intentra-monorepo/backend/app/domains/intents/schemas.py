"""What the client sends to intent routes."""
import uuid

from pydantic import BaseModel, Field


class IntentIn(BaseModel):
    text: str = Field(min_length=4, max_length=1000)
    intent_id: uuid.UUID | None = Field(default=None, description="answer a clarifying question about an existing request")
