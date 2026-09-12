"""POST /v1/webhooks/arc — an internal fast path: fetch the receipt now instead of waiting for the next poll."""
import hashlib
import hmac

from fastapi import APIRouter, Header, Request

from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.errors import NotFound, Unauthorized
from app.domains.payments.schemas import WebhookIn
from app.integrations.arc.events import DecodedLog
from app.orchestration.chain_events import handle_log, receipt_logs

router = APIRouter(tags=["webhooks"])


def _check(raw: bytes, signature: str) -> None:
    expected = hmac.new(get_settings().internal_webhook_secret.get_secret_value().encode(), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, (signature or "").removeprefix("sha256=")):
        raise Unauthorized("bad webhook signature", code="invalid_token")


class SimulatedEvent(BaseModel):
    """A synthetic escrow log, so the whole flow can be demonstrated before the contract is deployed."""
    name: str
    tx_key: str
    args: dict
    tx_hash: str
    log_index: int = 0
    block_number: int = 1


@router.post("/webhooks/arc", summary="Internal: a transaction hash to look at now")
async def arc(request: Request, x_intentra_signature: str = Header(default="")) -> dict:
    raw = await request.body()
    _check(raw, x_intentra_signature)
    body = WebhookIn.model_validate_json(raw)
    count, status = await receipt_logs(body.tx_hash)
    return {"tx_hash": body.tx_hash, "logs": count, "status": status}


@router.post("/webhooks/simulate", include_in_schema=False)
async def simulate(request: Request, x_intentra_signature: str = Header(default="")) -> dict:
    """Dev only. Feeds a synthetic escrow event to the same handler the watcher uses, so `scripts/demo_run.py`
    can walk the whole lifecycle without a deployed contract. Refused unless ENV=dev, and HMAC-signed like /webhooks/arc."""
    settings = get_settings()
    if settings.env != "dev":
        raise NotFound("not found")
    raw = await request.body()
    _check(raw, x_intentra_signature)
    event = SimulatedEvent.model_validate_json(raw)
    await handle_log(DecodedLog(name=event.name, tx_hash=event.tx_hash.lower(), log_index=event.log_index,
                                block_number=event.block_number, contract=settings.escrow_address.lower(),
                                tx_key=event.tx_key.lower(), args=event.args))
    return {"simulated": event.name, "tx_key": event.tx_key}
