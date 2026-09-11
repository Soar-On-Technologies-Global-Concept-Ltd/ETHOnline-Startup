**Intentra --- API Specification**

*Intentra*

Version: September 2026

# 1. API Philosophy

The Transaction Assurance API exposes the same core capabilities used by
Intentra\'s first-party experiences. External agents should not receive
privileged shortcuts around authorization.

# 2. Core Resources

  -----------------------------------------------------------------------
  Resource                            Purpose
  ----------------------------------- -----------------------------------
  Intents                             Structured representation of user
                                      goals and constraints

  Policies                            Rules governing autonomous actions

  Authorizations                      Explicit permission decisions

  Quotes                              Provider offers

  Transactions                        Canonical transaction record

  Payments                            Payment attempts and reconciliation

  Fulfillment                         Progress and completion

  Evidence                            Artifacts supporting the
                                      transaction

  Complaints                          Customer/provider issues

  Disputes                            Formal contested outcomes

  Resolutions                         Decision and remedy

  Trust                               Provider performance signals
  -----------------------------------------------------------------------

# 3. Initial Endpoints

-   POST /v1/intents

-   POST /v1/authorizations

-   POST /v1/policies

-   POST /v1/quotes

-   POST /v1/transactions

-   GET /v1/transactions/:id

-   POST /v1/transactions/:id/authorize

-   POST /v1/transactions/:id/payment

-   POST /v1/transactions/:id/fulfillment

-   POST /v1/transactions/:id/evidence

-   POST /v1/transactions/:id/complaints

-   POST /v1/transactions/:id/disputes

-   POST /v1/transactions/:id/resolve

-   GET /v1/providers/:id/trust

# 4. Example Intent

{\"goal\":\"paint
apartment\",\"location\":\"Lagos\",\"budget\":{\"max\":250000,\"currency\":\"NGN\"},\"requirements\":\[\"3
bedrooms\",\"living room\",\"2 coats\"\]}

# 5. Authorization Contract

Authorization should record actor, policy, scope, maximum amount,
currency, permitted merchant/provider constraints, expiration, decision
and reason.

# 6. Idempotency

Payment, transaction creation, state transitions and other
side-effecting endpoints should support idempotency keys.

# 7. Agent Security

-   Agents authenticate separately from users.

-   Agents receive scoped permissions.

-   Permissions have explicit lifetime and limits.

-   Agents cannot alter their own policies.

-   High-risk actions require user approval.

-   Every agent action maps to a transaction and audit event.

# 8. Versioning

Use /v1 for the first stable API. Breaking changes require a new major
version.
