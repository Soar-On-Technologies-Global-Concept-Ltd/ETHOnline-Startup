"""Settings from the environment (section 20.1 of the schematics). Refuses to start with unsafe test fakes outside dev or test."""
from functools import lru_cache
from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PLACEHOLDER_SECRETS = {"dev-only-change-me", "change-me", "changeme", "secret"}

# Managed Postgres (Render, Heroku, Fly, Neon) hands out a libpq URL. Two things in it break this app: the driver
# resolves to psycopg2, which the image does not install, and libpq-only query parameters make asyncpg raise
# TypeError on connect. Both surface as a boot crash on the platform and never locally, so normalise on the way in.
ASYNCPG_SCHEMES = {"postgres", "postgresql", "postgresql+psycopg2", "postgresql+psycopg"}
LIBPQ_ONLY_PARAMS = {"sslmode", "channel_binding", "gssencmode", "target_session_attrs"}
TLS_SSLMODES = {"require", "verify-ca", "verify-full"}


def normalise_database_url(raw: str) -> tuple[str, bool]:
    """Return (url asyncpg can open, whether the URL asked for TLS)."""
    parts = urlsplit(raw)
    scheme = "postgresql+asyncpg" if parts.scheme in ASYNCPG_SCHEMES else parts.scheme
    kept, requires_tls = [], False
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        if key == "sslmode":
            requires_tls = value in TLS_SSLMODES
        elif key not in LIBPQ_ONLY_PARAMS:
            kept.append((key, value))
    return urlunsplit((scheme, parts.netloc, parts.path, urlencode(kept), parts.fragment)), requires_tls


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: Literal["dev", "test", "staging", "prod"] = "dev"
    database_url: str = "postgresql+asyncpg://intentra@127.0.0.1:5432/intentra"
    database_requires_tls: bool = False   # set from the URL's sslmode; asyncpg takes it as a connect argument
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000", "https://intentra-theta.vercel.app"])
    log_level: str = "INFO"
    public_base_url: str = "http://localhost:8000"
    signing_secret: SecretStr = SecretStr("dev-only-change-me")
    internal_webhook_secret: SecretStr = SecretStr("dev-only-change-me")

    # Arc
    arc_rpc_url: str = "https://rpc.testnet.arc.io"
    arc_chain_id: int = 5042002
    escrow_address: str = "0xeF3a099CC877F6e274b037847A6ee44C4d62648D"   # live on Arc testnet
    escrow_deploy_block: int = 61719028   # the block IntentraEscrow was deployed in
    usdc_address: str = "0xFa5a5744898B71c93fF80F179d95184864143190"     # the escrow's 6-decimal mock USDC
    resolver_private_key: SecretStr | None = None   # the AI arbitrator key: one of the three signers
    confirmations: int = 1
    explorer_base_url: str = "https://testnet.arcscan.app"
    min_max_fee_gwei: int = 20
    log_range_blocks: int = 2000

    # Privy
    privy_app_id: str = ""
    privy_verification_key: str = ""
    privy_app_secret: SecretStr | None = None
    privy_mode: Literal["live", "fake"] = "live"

    # World Selfie Check
    world_app_id: str = ""
    world_rp_id: str = ""
    world_rp_signing_key: SecretStr | None = None
    world_verify_base_url: str = "https://developer.world.org"
    world_action_authorize: str = "authorize-transaction"
    world_action_complaint: str = "file-complaint"
    world_mode: Literal["live", "fake"] = "live"

    # AgentService
    llm_provider: Literal["anthropic", "fake", "openai"] = "anthropic"
    llm_base_url: str | None = None
    llm_api_key: SecretStr | None = None
    llm_model: str = "claude-opus-5"
    ai_timeout_seconds: float = 20.0

    # TrustService
    graph_query_url: str = ""
    graph_api_key: SecretStr | None = None
    graph_timeout_seconds: float = 3.0
    trust_min: int = 40

    # Evidence storage
    storage_backend: Literal["local", "s3"] = "local"
    local_storage_dir: str = "./.data/evidence"
    storage_endpoint: str = ""
    storage_bucket: str = "intentra-evidence"
    storage_region: str = "auto"
    storage_access_key: SecretStr | None = None
    storage_secret_key: SecretStr | None = None
    signed_url_ttl_seconds: int = 300
    max_upload_bytes: int = 8 * 1024 * 1024

    # Money and policy
    demo_fx_rate_ngn_per_usdc: int = 1650
    policy_hard_cap_ngn: int = 250_000
    ask_tolerance_bps: int = 1000

    # Timers (seconds)
    quote_ttl_seconds: int = 1800
    authorization_ttl_seconds: int = 900
    dispute_window_seconds: int = 600
    delivery_deadline_seconds: int = 7200
    complaint_margin_seconds: int = 60
    response_window_seconds: int = 600
    accept_window_seconds: int = 900

    # Dispute ladder
    l2_min_confidence: float = 0.6
    l2_max_amount_minor: int = 151_515_151

    # Workers
    workers_enabled: bool = True
    watch_interval_seconds: float = 3.0
    reconcile_interval_seconds: float = 15.0
    outbox_poll_seconds: float = 2.0

    @model_validator(mode="after")
    def _database_url_is_one_asyncpg_can_open(self) -> "Settings":
        self.database_url, requires_tls = normalise_database_url(self.database_url)
        self.database_requires_tls = self.database_requires_tls or requires_tls
        return self

    @model_validator(mode="after")
    def _escrow_is_pinned_outside_dev(self) -> "Settings":
        """A deployment that never learned where the escrow is, or when it was deployed, fails quietly rather than
        loudly: the watcher starts at the chain head and simply never sees an event that happened before boot."""
        if self.env in ("staging", "prod"):
            problems = []
            if int(self.escrow_address, 16) == 0:
                problems.append("ESCROW_ADDRESS is the zero address")
            if self.escrow_deploy_block <= 0:
                problems.append("ESCROW_DEPLOY_BLOCK is not set, so the watcher would start at the chain head and "
                                "miss every event before it")
            if problems:
                raise ValueError("; ".join(problems))
        return self

    @model_validator(mode="after")
    def _no_placeholder_secrets_outside_dev(self) -> "Settings":
        """A deployment that kept the sample secrets would sign evidence URLs and webhooks with a public value."""
        if self.env in ("staging", "prod"):
            weak = [name for name, value in (("SIGNING_SECRET", self.signing_secret),
                                             ("INTERNAL_WEBHOOK_SECRET", self.internal_webhook_secret))
                    if value.get_secret_value() in PLACEHOLDER_SECRETS or len(value.get_secret_value()) < 16]
            if weak:
                raise ValueError(f"{', '.join(weak)} must be set to a real secret of at least 16 characters when ENV is "
                                 f"{self.env}")
        return self

    @model_validator(mode="after")
    def _no_fakes_outside_dev(self) -> "Settings":
        fakes = [n for n, v in (("PRIVY_MODE", self.privy_mode), ("WORLD_MODE", self.world_mode), ("LLM_PROVIDER", self.llm_provider)) if v == "fake"]
        if fakes and self.env in ("staging", "prod"):
            raise ValueError(f"{', '.join(fakes)}=fake is only allowed when ENV is dev or test")
        return self

    @property
    def explorer_tx_url(self) -> str:
        return self.explorer_base_url.rstrip("/") + "/tx/"


@lru_cache
def get_settings() -> Settings:
    return Settings()
