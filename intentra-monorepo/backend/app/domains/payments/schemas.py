"""Chain ingress shapes."""
from pydantic import BaseModel, Field

from app.core.schemas import TX_HASH


class WebhookIn(BaseModel):
    tx_hash: str = Field(pattern=TX_HASH)
