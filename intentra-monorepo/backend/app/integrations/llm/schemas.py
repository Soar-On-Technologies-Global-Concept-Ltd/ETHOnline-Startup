"""Shapes the model must return (schematics §10). The core validates every one before use; none of them can move money."""
import datetime as dt
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AfterValidator, BaseModel, Field, model_validator

from app.core.remedies import Remedy


def _clip(limit: int) -> AfterValidator:
    return AfterValidator(lambda v: " ".join(v.split())[:limit])


Short = Annotated[str, _clip(160), Field(description="plain language, at most 160 characters")]
Question = Annotated[str, _clip(200), Field(description="one short question, at most 200 characters")]
Rationale = Annotated[str, _clip(600), Field(description="plain language, at most 600 characters")]
Requirement = Annotated[str, _clip(60)]


class IntentSpec(BaseModel):
    service: Literal["painting"]
    area: str = Field(min_length=2, max_length=60)
    rooms: int = Field(ge=1, le=10)
    budget_max_naira: int = Field(ge=1_000, le=10_000_000, description="whole naira, for example 180000 for ₦180k")
    date: dt.date
    requirements: list[Requirement] = Field(default_factory=list, max_length=10)


class IntentResult(BaseModel):
    """Either a complete spec or one clarifying question, never both."""
    spec: IntentSpec | None = None
    clarifying_question: Question | None = None

    @model_validator(mode="after")
    def exactly_one(self) -> "IntentResult":
        if (self.spec is None) == (self.clarifying_question is None):
            raise ValueError("return a spec or a clarifying question, not both")
        return self


class RecText(BaseModel):
    quote_id: UUID
    why: Short
    trade_offs: Short


class RecTexts(BaseModel):
    items: list[RecText] = Field(max_length=10)


class CoverageNote(BaseModel):
    scope_item: str = Field(max_length=40)
    status: Literal["covered", "unclear", "missing"]
    note: Short


class CoverageNotes(BaseModel):
    items: list[CoverageNote] = Field(max_length=20)


class RemedyProposal(BaseModel):
    """Exactly one remedy from the fixed set, citing evidence from the catalog."""
    remedy: Remedy
    cited_evidence_ids: list[UUID] = Field(min_length=1)
    rationale: Rationale
    confidence: float = Field(ge=0, le=1)
