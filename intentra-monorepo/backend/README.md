# Intentra — backend

One accountable transaction, end to end: a sentence becomes a structured job, the customer authorises it with a
signature and a Selfie Check, USDC sits in an Arc escrow, evidence is hashed and anchored, and the money is released
or split **only** as the two parties agreed.

> **AI proposes → Policy checks → the human authorises → the contract executes.**
> The Transaction is the centre; Authorization, Fulfillment and Payment hang off it.

FastAPI modular monolith with three services, exactly the MVP scope declared in
`Intentra_Architecture_Docs/05_Hackathon_Submission.md`:

| 05 service | Here | Partner |
|---|---|---|
| AgentService | `app/services/ai/` | Claude (`claude-opus-5`) — structured output, no tools, no authority |
| TrustService | `app/services/trust/` | The Graph — `subgraph/intentra-arc` on Arc, live data only |
| PaymentService | `app/services/blockchain/` | Arc — `IntentraEscrow` + USDC (6-decimal ERC-20 interface) |
| Identity | `app/services/identity/` | Privy (email login, embedded wallets, EIP-712) · World Selfie Check |

The full design, every diagram and every rule: `docs/16_Intentra_ETHOnline_Backend_Schematics.docx`.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt      # or: pip install -e ".[dev]"
cp .env.example .env                 # for a local demo: ENV=dev, PRIVY_MODE/WORLD_MODE=fake, LLM_PROVIDER=fake
docker compose up -d postgres        # or point DATABASE_URL at your own
alembic upgrade head
python scripts/seed.py               # three painters with labelled history
uvicorn app.main:app --reload
```

Then walk both demo paths end to end, twice, with no manual database edits:

```bash
python scripts/demo_run.py --path both --times 2
```

`docs`: <http://localhost:8000/docs> · health: <http://localhost:8000/healthz>

### Modes

`PRIVY_MODE`, `WORLD_MODE` and `LLM_PROVIDER` accept `fake` so the whole flow runs without partner keys — refused
outright when `ENV` is `staging` or `prod`. In fake mode a bearer token is `test:<id>:<wallet>:<email>`.

With no escrow deployed, `scripts/demo_run.py` feeds synthetic events to the same handler the watcher uses, through
the dev-only `POST /v1/webhooks/simulate` (needs `ENV=dev` and the internal HMAC). Against a real Arc deployment the
wallets send the calls the API returns and the watcher applies the money states from the real events — no other
difference in the code path.

## How it fits together

```
POST /v1/intents      AgentService parses the sentence          CREATED → INTENT_STRUCTURED
GET  …/recommendations deterministic ranking + Graph trust      (AI writes only the why and trade-offs)
POST /v1/transactions  quote bound, typed data issued           → QUOTE_SELECTED → AWAITING_AUTHORIZATION
POST …/authorize       signature + Selfie Check + policy        → AUTHORIZED
POST …/fund            approve + fund call data                 → FUNDING …  JobFunded → FUNDED
POST …/start · /evidence · /deliver                             → IN_PROGRESS → EVIDENCE_SUBMITTED · Submitted → DELIVERED
POST …/release                                    Released      → RELEASED
POST …/complaint  →  respond  →  proposal  →  accept ×2         DisputeOpened → DISPUTED → RESOLVING → PROPOSED · Resolved → SETTLED
```

Eight rules hold the whole thing together:

1. **Only the state machine writes `transactions.state`** (`app/services/state/machine.py`; a test enforces it by AST scan).
2. **Money states commit on chain events only.** The API requests; the watcher applies FUNDED, DELIVERED, RELEASED,
   DISPUTED, SETTLED and refund-CANCELLED after checking every field of the event.
3. **AI returns validated data, never authority.** Fixed remedy set, splits from `REMEDY_BPS`, cited evidence must
   belong to the transaction, low confidence escalates.
4. **Policy runs before every high-impact action** — ALLOW / ASK / BLOCK, deterministic Python, never a model.
5. **Insert-only** authorizations, complaints, acceptances and audit events (database triggers, not just discipline).
6. **Everything idempotent**: `Idempotency-Key` on the money routes, `(tx_hash, log_index)` on chain events,
   unique nullifiers per action and transaction.
7. **Integer minor units** everywhere: kobo for naira, micro-USDC (6 decimals) for escrow.
8. **Verify outside, write inside**: signatures, World, the model and The Graph are checked before the row is locked.

## Layout

A modular monolith, organised by domain rather than by layer. Each domain owns its own router, models, schemas and
service, and reaches other domains only through their service functions — never their tables.

```
app/
  main.py                     mounts each domain's router
  core/                       shared kernel: config · db · errors · json · money · hashing · states · remedies · policy/
                              idempotency · columns · http        (knows nothing about domains, adapters or the web)
  integrations/               outbound adapters: arc/ · privy · world · graph · storage · llm/
                              (an anti-corruption layer; never imports a domain)
  domains/
    identity/                 router · models · schemas · service · deps      users · human_checks
    providers/                router · models · schemas · service · trust · ranking · score · ai      providers
    intents/                  router · models · schemas · service · ai        intents · quotes
    transactions/             router · models · schemas · service · machine · policy · views · deps   transactions
    authorization/            router · models · schemas · service             authorizations
    payments/                 router · models · schemas · service · outbox · resolver   payments · chain_txs · blockchain_events
    fulfillment/              router · models · schemas · service             fulfillments
    evidence/                 router · models · schemas · service · sanitize  evidence
    disputes/                 router · models · schemas · service · ladder · coverage · proposer   complaints · disputes · proposals · acceptances
    audit/                    models · service                                audit_events
    registry.py               imports every domain's tables for Alembic and create_all
  orchestration/              chain_events.py — the one place escrow logs are applied across domains
  system/                     health.py · webhooks.py (internal chain ingress)
  workers/                    leader · blockchain · evidence · reconciliation · runner
```

**The rules the structure enforces** (`lint-imports`, 14 contracts):

- **Layered**: `system` and `workers` sit above `orchestration`, then `domains`, then `integrations`, then `core`.
- **The kernel is ignorant**: `core` may not import a domain, an adapter, or FastAPI — which is why the exception
  types live in `core/errors.py` and only the handler wiring in `core/error_handlers.py` knows about the web.
- **Adapters never reach back**: `integrations` may not import a domain.
- **Tables are private**: no domain may import another domain's `models`; it calls that domain's service. The single
  deliberate exception is `transactions.models` — the Transaction is the aggregate root the product is built around,
  and the state machine remains its only writer (proved by an AST scan in `tests/test_single_writer.py`).
- **Routers stay thin**: no route may import a partner adapter.

Adding a feature usually means touching one folder. Splitting a domain out into its own service later means moving one
folder and replacing its service calls with HTTP — which is the point.

## Tests

```bash
pytest                    # pure: transitions, policy, money, hashing, EIP-712, World vectors, AI validation, trust, evidence
pytest -m db              # both demo paths end to end, plus the abuse cases in tests/test_security_db.py
lint-imports              # 14 architecture contracts: layering, kernel purity, thin routers, private tables
cd contracts && forge install foundry-rs/forge-std && forge test   # 24 tests: conservation, access control,
                          # settle-once, cross-job signature replay, a stolen resolver key, refunds
```

`shared/eip712.vectors.json` is signed by the same fixed key in the API and web test suites, so both check the same bytes.
`alembic check` is part of the loop too: the tables live in each domain now, and it proves the SQL did not move with them.

## Security

The abuse cases are tests, not prose — `tests/test_security_db.py` drives them over HTTP and
`contracts/test/IntentraEscrowSecurity.t.sol` drives them against the escrow:

- A non-party gets **404**, not 403: they do not learn that a transaction exists, and never see its `tx_key`.
- A signature from the wrong wallet, a Selfie Check replayed on the same job, an idempotency key reused with a
  different body, a forged webhook HMAC and a forged evidence link are each refused.
- The dev-only chain simulator is unreachable unless `ENV=dev`, even with a correct HMAC.
- Uploads are sniffed from their bytes, not their `Content-Type`, and are refused before the job starts.
- On-chain: a stolen resolver key cannot settle alone, cannot forge a party's signature, cannot pay a third party
  and cannot replay a resolution signed for another job. Every split conserves the amount (fuzzed).
- Staging and production refuse to start with the sample secrets or with any partner in `fake` mode.

## Deploying

1. Deploy `contracts/src/IntentraEscrow.sol` with the USDC ERC-20 interface (`0x3600…0000`) and the resolver address;
   put the address and deploy block in `.env`, then run `python scripts/export_shared.py`.
2. Deploy `subgraph/intentra-arc` (Subgraph Studio) and set `GRAPH_QUERY_URL`.
3. Set the Privy and World keys, switch the modes to `live`, set `ENV=staging` or `prod`, and fund the resolver with a
   little USDC — gas on Arc is paid in USDC, and the sender never bids below the 20 gwei floor.
4. `alembic upgrade head`, then run the API. Workers start only on the instance holding the Postgres advisory lock.

## Notes for judges

- Verified partner facts (chain ID, addresses, decimals, API shapes) were checked on 11 September 2026 and are cited
  in the schematics document; re-check before submission.
- Written with Claude Code (Claude Opus 5). The specs it worked from are in `docs/`.
