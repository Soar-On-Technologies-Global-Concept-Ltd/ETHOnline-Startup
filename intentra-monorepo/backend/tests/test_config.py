"""The settings a deployment must not start with (schematics §19, §20.1)."""
import pytest
from pydantic import ValidationError

from app.core.config import Settings

REAL_SECRET = "b8c1f0a4d93e47128f6a20bd5c7e9134"


def settings(**overrides) -> Settings:
    """Explicit values only: never the developer's own .env or shell."""
    base = {"_env_file": None, "env": "prod", "signing_secret": REAL_SECRET, "internal_webhook_secret": REAL_SECRET,
            "privy_mode": "live", "world_mode": "live", "llm_provider": "anthropic"}
    return Settings(**{**base, **overrides})


def test_a_production_deployment_is_fine_with_real_settings():
    assert settings().env == "prod"


@pytest.mark.parametrize("field", ["signing_secret", "internal_webhook_secret"])
def test_production_refuses_the_sample_secret(field: str):
    with pytest.raises(ValidationError, match="real secret"):
        settings(**{field: "dev-only-change-me"})


@pytest.mark.parametrize("field", ["signing_secret", "internal_webhook_secret"])
def test_production_refuses_a_short_secret(field: str):
    with pytest.raises(ValidationError, match="16 characters"):
        settings(**{field: "tooshort"})


@pytest.mark.parametrize("mode", [{"privy_mode": "fake"}, {"world_mode": "fake"}, {"llm_provider": "fake"}])
def test_production_refuses_the_test_doubles(mode: dict):
    with pytest.raises(ValidationError, match="only allowed when ENV is dev or test"):
        settings(**mode)


def test_staging_is_held_to_the_same_bar():
    with pytest.raises(ValidationError):
        settings(env="staging", signing_secret="dev-only-change-me")


def test_development_keeps_the_convenient_defaults():
    relaxed = settings(env="dev", signing_secret="dev-only-change-me", privy_mode="fake", world_mode="fake",
                       llm_provider="fake")
    assert relaxed.privy_mode == "fake" and relaxed.env == "dev"
