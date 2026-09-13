# Intentra — backend

One accountable transaction, end to end: a sentence becomes a structured job, the customer authorises it with a
signature and a Selfie Check, USDC sits in an Arc escrow, evidence is hashed and audited, and the money is released
or split **only** as the two parties signed for.

> **AI proposes → Policy checks → the human authorises → the contract executes.**
> The Transaction is the centre; Authorization, Fulfillment and Payment hang off it.

FastAPI modular monolith. The MVP scope:

| Service | Here | Partner |
|---|---|---|
| AgentService | `app/integrations/llm/` + each domain's `ai.py` | Claude (`claude-opus-5`) — structured output, no authority |
| TrustService | `app/domains/providers/trust.py` | The Graph — `subgraph/intentra-arc`, live data only |
| PaymentService | `app/domains/payments/` + `app/integrations/arc/` | Arc — the canonical `IntentraEscrow` |
| Identity | `app/domains/identity/` | Privy (email login, embedded wallets, EIP-712) · World Selfie Check |

Full design, diagrams and rules: `docs/16_Intentra_ETHOnline_Backend_Schematics.docx`.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt   # or: pip install -e ".[dev]"
cp .env.example .env                  # local demo: ENV=dev, PRIVY_MODE/WORLD_MODE=fake, LLM_PROVIDER=fake
docker compose up -d postgres         # or point DATABASE_URL at your own
alembic upgrade head
python scripts/seed.py                # three painters with labelled history
uvicorn app.main:app --reload
python scripts/demo_run.py --path both --times 2   # both demo paths, twice, no manual database edits
```

docs: <http://localhost:8000/docs> · health: <http://localhost:8000/healthz>

`PRIVY_MODE`, `WORLD_MODE` and `LLM_PROVIDER` accept `fake`, so the flow runs without partner keys — refused when
`ENV` is `staging` or `prod`. In fake mode a bearer token is `test:<id>:<wallet>:<email>`.

Without a funded escrow, `demo_run.py` feeds synthetic events to the same handler the watcher uses, via the dev-only
`POST /v1/webhooks/simulate` (`ENV=dev` plus the internal HMAC). Against real Arc the wallets send the calls the API
returns and the watcher applies the money states from real events — no other difference in the code path.

## How it fits together

```
POST /v1/intents       AgentService parses the sentence         CREATED → INTENT_STRUCTURED
GET  …/recommendations deterministic ranking + Graph trust      (AI writes only the why and trade-offs)
POST /v1/transactions  quote bound, typed data issued           → QUOTE_SELECTED → AWAITING_AUTHORIZATION
POST …/authorize       signature + Selfie Check + policy        → AUTHORIZED
POST …/fund            createIntent, then approve + fundIntent  → FUNDING …  IntentFunded → FUNDED
POST …/start · /evidence · /deliver                             → IN_PROGRESS → EVIDENCE_SUBMITTED → DELIVERED
POST …/release         both parties sign ResolveIntent          IntentResolved → RELEASED
POST …/complaint → respond → proposal → accept ×2               DisputeRaised → DISPUTED → RESOLVING → PROPOSED → SETTLED
```

Eight rules hold the whole thing together:

1. **Only the state machine writes `transactions.state`** — `app/domains/transactions/machine.py`, enforced by an AST
   scan in `tests/test_single_writer.py`.
2. **Money states commit on chain events only.** The API requests; the watcher applies FUNDED, RELEASED, DISPUTED,
   SETTLED and refund-CANCELLED after checking every field of the event.
3. **AI returns validated data, never authority.** Fixed remedy set, splits from `REMEDY_BPS`, cited evidence must
   belong to the transaction, low confidence escalates.
4. **Policy runs before every high-impact action** — ALLOW / ASK / BLOCK, deterministic Python, never a model.
5. **Insert-only** authorizations, complaints, acceptances and audit events — database triggers, not discipline.
6. **Everything idempotent**: `Idempotency-Key` on the money routes, `(tx_hash, log_index)` on chain events, unique
   nullifiers per action and transaction.
7. **Integer minor units** everywhere: kobo for naira, micro-USDC (6 decimals) for escrow.
8. **Verify outside, write inside**: signatures, World, the model and The Graph are checked before the row is locked.

## Layout

Organised by domain, not by layer. Each domain owns its router, models, schemas and service, and reaches other
domains only through their service functions — never their tables.

```
app/
  main.py           mounts each domain's router
  core/             shared kernel: config · db · errors · json · money · hashing · states · remedies · policy/
                    idempotency · columns · http · explanation · status_copy
  integrations/     outbound adapters: arc/ · llm/ · privy · world · graph · storage
  domains/
    identity/       users · human_checks
    providers/      providers                    (+ trust · ranking · score · ai)
    intents/        intents · quotes             (+ ai)
    transactions/   transactions                 (+ machine · policy · views · deps)
    authorization/  authorizations
    payments/       payments · chain_txs · blockchain_events   (+ outbox · resolver)
    fulfillment/    fulfillments
    evidence/       evidence                     (+ sanitize)
    disputes/       complaints · disputes · proposals · acceptances   (+ ladder · coverage · proposer)
    audit/          audit_events
    registry.py     imports every domain's tables for Alembic
  orchestration/    chain_events.py — the one place escrow logs are applied across domains
  system/           health.py · webhooks.py (internal chain ingress)
  workers/          leader · blockchain · reconciliation · runner
```

`lint-imports` enforces 14 contracts: the layering above (`system`/`workers` → `orchestration` → `domains` →
`integrations` → `core`); `core` imports no domain, adapter or FastAPI; `integrations` never imports a domain; no
domain imports another's `models`; no router imports a partner adapter. The one deliberate exception is
`transactions.models` — the Transaction is the aggregate root, and the state machine stays its only writer.

## The escrow

The contract is **not** in this repository. It lives in `intentra-monorepo/contracts`, owned by the contracts team;
this backend integrates with the ABI they publish in `contracts/exports/intentra-contracts.ts`, vendored here as
`shared/abi/IntentraEscrow.json`.

Live on Arc testnet (chain 5042002): escrow `0xeF3a099CC877F6e274b037847A6ee44C4d62648D`, USDC (6 dp)
`0xFa5a5744898B71c93fF80F179d95184864143190`.

What that contract's shape means here:

- **Jobs are keyed by the escrow's `uint256 intentId`**, not our `tx_key`, so funding is two phases: the wallet sends
  `createIntent`, the watcher reads `IntentCreated` for the id (`transactions.escrow_intent_id`), and only then does
  the API return `approve` + `fundIntent`.
- **There is no `release`.** Paying in full is a resolution: the customer signs `ResolveIntent` (everything to the
  provider) and the arbitrator co-signs — two of the three signers `executeWithSignatures` requires.
- **There is no `submit` and no `anchorEvidence`.** Delivery is Intentra's own record; evidence is hashed, stored
  privately and written into the audit chain, not anchored on-chain. Trust comes from funded, resolved, disputed and
  refunded counts.
- **Settlement uses exact amounts**, not basis points. `REMEDY_BPS` still decides the split internally; the amounts it
  produces are what both parties sign and what the contract pays.
- **Two of three distinct signers** from {customer, provider, AI arbitrator}, so the arbitrator key alone can never pay
  anyone. Splits here are signed by both humans. Note the contract *would* accept AI + one party, and
  `executeAbandonment` executes a standing AI proposal after 14 days of silence (full refund if there is no proposal).
- **The dispute clock is the contract's**: `submitAIProposal` opens a 48-hour window in which either party can stake to
  escalate to a human; the owner settles appeals with `resolveHumanAppeal`.
- **Nothing auto-releases.** A delivered job the customer never signs for waits for a signature or the 14-day
  abandonment timeout, which the reconciliation worker queues.

## Tests

```bash
pytest              # transitions, policy, money, hashing, EIP-712, World vectors, AI validation, trust, evidence
pytest -m db        # both demo paths end to end, plus the abuse cases in tests/test_security_db.py
lint-imports        # the 14 architecture contracts
alembic check       # proves the SQL did not drift when the tables moved into their domains
cd ../contracts && forge test    # the escrow itself, owned by the contracts team
```

`shared/eip712.vectors.json` is signed by the same fixed key in the API and web test suites, so both check the same bytes.

## Security

The abuse cases are tests, not prose — `tests/test_security_db.py` over HTTP and
`../contracts/test/IntentraEscrowSecurity.t.sol` against the escrow:

- A non-party gets **404**, not 403: they never learn a transaction exists, and never see its `tx_key`.
- A signature from the wrong wallet, a Selfie Check replayed on the same job, an idempotency key reused with a
  different body, a forged webhook HMAC and a forged evidence link are each refused.
- The dev-only chain simulator is unreachable unless `ENV=dev`, even with a correct HMAC.
- Uploads are sniffed from their bytes, not their `Content-Type`, and refused before the job starts.
- On-chain: `executeWithSignatures` needs two distinct signers and the amounts must sum to the escrow, so a stolen
  arbitrator key pays no one by itself; `ResolveIntent` binds each signature to one `intentId` and one pair of
  amounts, so nothing replays onto another job.
- Staging and production refuse to start with the sample secrets or with any partner in `fake` mode.

## Deploying

1. Set `ESCROW_ADDRESS` and `ESCROW_DEPLOY_BLOCK` in `.env` from the contracts team's deployment, then run
   `python scripts/export_shared.py`.
2. Deploy `subgraph/intentra-arc` (Subgraph Studio) and set `GRAPH_QUERY_URL`.
3. Set the Privy and World keys, switch the modes to `live`, set `ENV=staging` or `prod`, and fund the
   arbitrator key (`RESOLVER_PRIVATE_KEY`) with a little USDC — gas on Arc is paid in USDC, and the sender
   never bids below the 20 gwei floor.
4. `alembic upgrade head`, then run the API. Workers start only on the instance holding the Postgres advisory lock.

### On Render

`render.yaml` at the repository root is a blueprint for a free Postgres and a Docker web service: in Render,
**New → Blueprint**, pick the repository, apply. By hand instead: a Web Service with Root Directory
`intentra-monorepo/backend`, runtime Docker, health check `/healthz`, and the blueprint's environment variables.

The container runs `scripts/start.sh`: migrate, optionally seed, then serve on `$PORT`. Four things the platform
does that would otherwise break the boot are handled for you — its `postgresql://` URL is rewritten to `asyncpg`,
an `?sslmode=require` becomes a TLS connect argument, `$PORT` is honoured, and `SEED_DEMO_DATA=true` populates the
three demo painters, since the free plan gives you no shell to seed an empty database from.

Pick `ENV` deliberately. `ENV=dev` keeps the HMAC-signed `POST /v1/webhooks/simulate` reachable, which is what
lets a demo walk a funding and a dispute without a customer wallet broadcasting, and it permits the `fake` partner
modes — so the service runs with no partner credentials at all. `ENV=staging` turns that route off and refuses
every `fake`, so it needs real Privy, World and Anthropic keys before it will start.

Two limits: free web services sleep after 15 idle minutes, which stops the chain watcher, and evidence stored with
`STORAGE_BACKEND=local` is lost on every deploy — use `s3` to keep it.

## Notes for judges

Partner facts (chain ID, addresses, decimals, API shapes) were verified on 11 September 2026 and cited in the
schematics document; re-check before submission. The specs are in `docs/`.
