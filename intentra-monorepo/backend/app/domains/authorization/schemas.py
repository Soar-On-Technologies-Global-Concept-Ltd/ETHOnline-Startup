"""What the customer sends when approving a job."""
from pydantic import BaseModel, Field

from app.core.schemas import SIGNATURE


class AuthorizeIn(BaseModel):
    signature: str = Field(pattern=SIGNATURE)
    idkit_result: dict
