"""Small helpers every router uses."""
from fastapi import Request

from app.core.errors import Unprocessable


def idempotency_key(request: Request, required: bool = True) -> str | None:
    key = request.headers.get("Idempotency-Key")
    if required and not key:
        raise Unprocessable("this action needs an Idempotency-Key header: one UUID per user action",
                            code="validation_error", details={"header": "Idempotency-Key"})
    if key and len(key) > 80:
        raise Unprocessable("Idempotency-Key is too long", code="validation_error")
    return key
