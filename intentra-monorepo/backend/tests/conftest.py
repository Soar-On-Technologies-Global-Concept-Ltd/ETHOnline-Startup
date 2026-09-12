"""Test defaults: fake partners, the local test database, and no background workers."""
import os

# Forced, not defaulted: a shell with ENV=dev exported must not silently run the suite in dev mode, which would
# leave the dev-only chain simulator reachable and quietly weaken the tests that prove it is not.
os.environ["ENV"] = "test"
os.environ["PRIVY_MODE"] = "fake"
os.environ["WORLD_MODE"] = "fake"
os.environ["LLM_PROVIDER"] = "fake"
os.environ["WORKERS_ENABLED"] = "false"
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://intentra@127.0.0.1:55432/intentra_test")
os.environ.setdefault("ESCROW_ADDRESS", "0xeF3a099CC877F6e274b037847A6ee44C4d62648D")
# The AI arbitrator: one of the escrow's three signers. A throwaway key, and never enough on its own.
os.environ.setdefault("RESOLVER_PRIVATE_KEY", "0x" + "d1" * 32)
os.environ.setdefault("USDC_ADDRESS", "0xFa5a5744898B71c93fF80F179d95184864143190")
os.environ.setdefault("SIGNING_SECRET", "test-signing-secret")
os.environ.setdefault("INTERNAL_WEBHOOK_SECRET", "test-webhook-secret")
os.environ.setdefault("STORAGE_BACKEND", "local")
os.environ.setdefault("LOCAL_STORAGE_DIR", "./.data/test-evidence")

import pytest  # noqa: E402

from app.integrations.llm.client import FakeLLM, set_llm  # noqa: E402


@pytest.fixture
def fake_llm() -> FakeLLM:
    llm = FakeLLM()
    set_llm(llm)
    yield llm
    set_llm(None)
