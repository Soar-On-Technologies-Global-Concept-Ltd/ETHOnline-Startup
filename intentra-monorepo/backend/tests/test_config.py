"""The settings a deployment must not start with (schematics §19, §20.1)."""
import pytest
from pydantic import ValidationError

from app.core.config import Settings, normalise_database_url

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


def test_production_refuses_an_unset_deploy_block():
    """Without it the watcher starts at the head, so an event a second old is invisible: silent, not loud."""
    with pytest.raises(ValidationError, match="ESCROW_DEPLOY_BLOCK"):
        settings(escrow_deploy_block=0)


def test_production_refuses_the_zero_escrow_address():
    with pytest.raises(ValidationError, match="zero address"):
        settings(escrow_address="0x" + "00" * 20)


def test_the_live_deployment_satisfies_both():
    live = settings(escrow_address="0xeF3a099CC877F6e274b037847A6ee44C4d62648D", escrow_deploy_block=61_719_028)
    assert live.escrow_deploy_block == 61_719_028


def test_development_keeps_the_convenient_defaults():
    relaxed = settings(env="dev", signing_secret="dev-only-change-me", privy_mode="fake", world_mode="fake",
                       llm_provider="fake")
    assert relaxed.privy_mode == "fake" and relaxed.env == "dev"


# --- the database URL a managed platform hands us -------------------------------------------------------------

def test_render_internal_url_becomes_an_asyncpg_url():
    """Render's own connection string names no driver, so SQLAlchemy would reach for psycopg2 and the image
    would crash on boot with ModuleNotFoundError — a failure that never appears locally."""
    url, tls = normalise_database_url("postgresql://intentra:pw@dpg-abc123-a:5432/intentra")
    assert url == "postgresql+asyncpg://intentra:pw@dpg-abc123-a:5432/intentra"
    assert tls is False


def test_the_heroku_style_postgres_scheme_is_rewritten_too():
    url, _ = normalise_database_url("postgres://u:p@host:5432/db")
    assert url.startswith("postgresql+asyncpg://")


def test_sslmode_becomes_a_connect_argument_rather_than_a_url_parameter():
    """asyncpg raises TypeError on sslmode, so it has to leave the URL and come back as connect_args."""
    url, tls = normalise_database_url(
        "postgresql://u:p@host.oregon-postgres.render.com/db?sslmode=require")
    assert "sslmode" not in url
    assert tls is True


def test_other_libpq_only_parameters_are_dropped():
    url, _ = normalise_database_url("postgresql://u@h/db?channel_binding=require&target_session_attrs=rw")
    assert "channel_binding" not in url and "target_session_attrs" not in url


def test_ordinary_query_parameters_survive():
    url, _ = normalise_database_url("postgresql://u@h/db?application_name=intentra&sslmode=disable")
    assert "application_name=intentra" in url


def test_a_url_that_is_already_correct_is_left_alone():
    raw = "postgresql+asyncpg://intentra@127.0.0.1:5432/intentra"
    url, tls = normalise_database_url(raw)
    assert (url, tls) == (raw, False)


def test_settings_normalise_on_construction(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@host/db?sslmode=verify-full")
    s = Settings(_env_file=None)
    assert s.database_url == "postgresql+asyncpg://u:p@host/db"
    assert s.database_requires_tls is True
