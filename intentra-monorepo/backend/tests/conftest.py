"""Test defaults: fake partners, the local test database, and no background workers."""
import os

os.environ.setdefault("ENV", "test")
os.environ.setdefault("PRIVY_MODE", "fake")
os.environ.setdefault("WORLD_MODE", "fake")
os.environ.setdefault("LLM_PROVIDER", "fake")
os.environ.setdefault("WORKERS_ENABLED", "false")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://intentra@127.0.0.1:55432/intentra_test")
os.environ.setdefault("ESCROW_ADDRESS", "0x00000000000000000000000000000000000E5C70")
os.environ.setdefault("USDC_ADDRESS", "0x3600000000000000000000000000000000000000")
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
