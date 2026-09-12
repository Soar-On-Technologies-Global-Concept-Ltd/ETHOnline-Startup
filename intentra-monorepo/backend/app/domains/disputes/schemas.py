"""What each side sends during a dispute."""
import uuid

from pydantic import BaseModel, Field

from app.core.schemas import SIGNATURE
from app.core.states import ComplaintCategory


class ComplaintIn(BaseModel):
    category: ComplaintCategory
    text: str = Field(min_length=4, max_length=2000)
    evidence_ids: list[uuid.UUID] = Field(min_length=1, max_length=10)
    idkit_result: dict


class RespondIn(BaseModel):
    text: str = Field(min_length=4, max_length=2000)


class AcceptIn(BaseModel):
    signature: str = Field(pattern=SIGNATURE)


class RejectIn(BaseModel):
    reason: str | None = Field(default=None, max_length=280)
