from pydantic import BaseModel, Field

class ProviderOnboardRequest(BaseModel):
    trade: str = Field(..., max_length=40, description="The primary service offered, e.g., Plumber")
    areas: list[str] = Field(default_factory=list, description="List of locations served")
    base_rate_minor: int = Field(..., description="Base hourly rate in the lowest currency denominator (e.g. kobo or cents)")
