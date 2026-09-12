"""What the client sends to identity routes."""
from typing import Literal

from pydantic import BaseModel, Field


class SessionIn(BaseModel):
    display_name: str | None = Field(default=None, max_length=80)


class RpSignatureIn(BaseModel):
    action: Literal["authorize-transaction", "file-complaint"]
