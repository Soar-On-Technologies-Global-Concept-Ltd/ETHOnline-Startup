"""Structured JSON logs with request and transaction context on every line; secrets are redacted."""
import contextvars
import json
import logging
import sys
from datetime import datetime, timezone

request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)
transaction_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("transaction_id", default=None)
user_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("user_id", default=None)

REDACT = ("authorization", "signature", "private_key", "secret", "idkit_result", "token", "api_key")


def _redact(value):
    if isinstance(value, dict):
        return {k: ("[redacted]" if any(r in k.lower() for r in REDACT) else _redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(v) for v in value]
    return value


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data = {"ts": datetime.now(timezone.utc).isoformat(), "level": record.levelname, "logger": record.name, "msg": record.getMessage(),
                "request_id": request_id_var.get(), "transaction_id": transaction_id_var.get(), "user_id": user_id_var.get()}
        extra = getattr(record, "fields", None)
        if isinstance(extra, dict):
            data.update(_redact(extra))
        if record.exc_info:
            data["exc"] = self.formatException(record.exc_info)
        return json.dumps({k: v for k, v in data.items() if v is not None}, default=str)


def setup_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)
    for noisy in ("httpx", "httpcore", "web3", "urllib3", "botocore"):
        logging.getLogger(noisy).setLevel("WARNING")


def log(logger: logging.Logger, msg: str, **fields) -> None:
    logger.info(msg, extra={"fields": fields})
