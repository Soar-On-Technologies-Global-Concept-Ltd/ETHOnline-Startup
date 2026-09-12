"""The Intentra API.

A modular monolith: each domain under `app/domains/` owns its router, models, schemas and service, and talks to other
domains through their service functions — never their tables. `core/` is the shared kernel, `integrations/` holds the
outbound adapters (Arc, Privy, World, The Graph, the model, storage), and `orchestration/` composes the few flows that
genuinely span domains. The layering is enforced by import-linter, not by convention.
"""
import logging
import time
import uuid

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.db import dispose_engine
from app.core.error_handlers import install_handlers
from app.core.logging import log, request_id_var, setup_logging, transaction_id_var, user_id_var
from app.domains.authorization.router import router as authorization_router
from app.domains.disputes.complaints import router as complaints_router
from app.domains.disputes.router import router as disputes_router
from app.domains.evidence.router import router as evidence_router
from app.domains.fulfillment.router import router as fulfillment_router
from app.domains.identity.router import router as identity_router
from app.domains.intents.router import router as intents_router
from app.domains.payments.router import router as payments_router
from app.system.webhooks import router as webhooks_router
from app.domains.providers.router import router as providers_router
from app.domains.transactions.router import router as transactions_router
from app.system.health import router as health_router
from app.workers import runner

logger = logging.getLogger("api")
settings = get_settings()

DESCRIPTION = """One accountable transaction, end to end: a sentence becomes a structured job, the customer authorises it
with a signature and a Selfie Check, USDC sits in an Arc escrow, evidence is hashed and anchored, and the money is
released or split only as the two parties agreed. AI proposes, policy checks, the human authorises, the contract executes."""

DOMAIN_ROUTERS = [identity_router, intents_router, providers_router, transactions_router, authorization_router,
                  payments_router, fulfillment_router, evidence_router, complaints_router, disputes_router]


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.log_level)
    log(logger, "starting", env=settings.env, workers=settings.workers_enabled)
    if settings.workers_enabled:
        await runner.start()
    try:
        yield
    finally:
        await runner.stop()
        await dispose_engine()
        log(logger, "stopped")


app = FastAPI(title="Intentra API", version="0.1.0", description=DESCRIPTION, lifespan=lifespan,
              openapi_url="/openapi.json", docs_url="/docs", redoc_url=None)
install_handlers(app)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=False,
                   allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
                   expose_headers=["X-Request-Id", "Idempotent-Replay"])


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
    request_id_var.set(request_id)
    transaction_id_var.set(None)
    user_id_var.set(None)
    started = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Request-Id"] = request_id
    log(logger, "request", route=request.url.path, method=request.method, status=response.status_code,
        duration_ms=round((time.perf_counter() - started) * 1000, 1))
    return response


for domain_router in DOMAIN_ROUTERS:
    app.include_router(domain_router, prefix="/v1")
app.include_router(webhooks_router, prefix="/v1")
app.include_router(health_router)


@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {"name": "Intentra API", "docs": "/docs", "health": "/healthz"}
