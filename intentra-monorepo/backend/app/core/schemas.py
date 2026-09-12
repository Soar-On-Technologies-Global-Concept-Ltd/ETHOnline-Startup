"""Request shapes shared by more than one domain."""
from pydantic import BaseModel, Field

SIGNATURE = r"^0x[0-9a-fA-F]{130}$"
TX_HASH = r"^0x[0-9a-fA-F]{64}$"


class ChainReportIn(BaseModel):
    tx_hash: str | None = Field(default=None, pattern=TX_HASH)
