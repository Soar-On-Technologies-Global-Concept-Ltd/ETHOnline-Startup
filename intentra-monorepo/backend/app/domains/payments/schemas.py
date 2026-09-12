"""Chain ingress shapes."""
from pydantic import BaseModel, Field

from app.core.schemas import SIGNATURE, TX_HASH


class WebhookIn(BaseModel):
    tx_hash: str = Field(pattern=TX_HASH)


class ReleaseIn(BaseModel):
    """Paying the provider in full is a resolution on the canonical escrow, so it needs the customer's signature.

    Send an empty body to get the typed data, then send it back signed.
    """
    signature: str | None = Field(default=None, pattern=SIGNATURE)
    tx_hash: str | None = Field(default=None, pattern=TX_HASH)
