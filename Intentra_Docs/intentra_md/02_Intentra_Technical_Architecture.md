**Intentra --- Technical Architecture**

*Intentra*

Version: September 2026

# 1. Architecture Goal

Build one reusable transaction-assurance backend that powers the
consumer marketplace, business procurement workflows and external
agent/API access.

# 2. Logical Architecture

USER / AI EXPERIENCE → MARKETPLACE OR EXTERNAL AGENT → TRANSACTION
ENGINE → AUTHORIZATION / MOOVE / FULFILLMENT → EVIDENCE → OUTCOME →
RESOLUTION → SETTLEMENT

# 3. Recommended Stack

  -----------------------------------------------------------------------
  Layer                               Technology
  ----------------------------------- -----------------------------------
  Web                                 React + TypeScript + Vite +
                                      Tailwind CSS

  API                                 NestJS + TypeScript

  Database                            PostgreSQL + Prisma

  Async jobs                          Redis + BullMQ

  Infrastructure                      Docker + cloud VM/container
                                      deployment

  API style                           REST + webhooks where supported

  Agent interfaces                    MCP/A2A later; not required for
                                      first MVP

  AI                                  Model-agnostic LLM service layer
  -----------------------------------------------------------------------

# 4. Core Services

-   Identity and organizations

-   Intent service

-   Recommendation service

-   Authorization/policy service

-   Quote/agreement service

-   Transaction service

-   Moove payment adapter

-   Fulfillment service

-   Evidence service

-   Outcome service

-   Complaint/dispute service

-   Resolution/refund service

-   Trust/reputation service

-   Notification service

-   Agent API gateway

# 5. Design Rule

The LLM is not the final authority. Deterministic services validate
identity, permissions, limits, transaction state, amounts and allowed
actions.

# 6. Transaction Integrity

-   Every transaction receives a unique transaction ID.

-   Every state transition is logged.

-   Payment operations are idempotent.

-   Authorization is stored as an immutable decision record.

-   Provider agreements are versioned.

-   Evidence is timestamped and associated with the transaction.

-   External callbacks are authenticated and reconciled.

# 7. Security

-   Server-side secrets

-   RBAC

-   Scoped API keys

-   Encryption in transit and at rest

-   Rate limiting

-   Webhook/signature verification where available

-   Audit logs

-   Idempotency keys

-   Prompt-injection defenses

-   Tool allowlists

-   Human escalation for high-risk cases

# 8. Scalability

Start as a modular monolith to move quickly. Keep domain boundaries
clean so high-volume services can later be extracted without rewriting
the product.

# 9. Deployment

-   Separate web and API deployments

-   Managed PostgreSQL where practical

-   Redis for jobs and short-lived state

-   Object storage for evidence

-   Centralized logs and metrics

-   Automated backups

-   CI/CD from GitHub

# 10. Reliability Targets

  -----------------------------------------------------------------------
  Area                                Initial target
  ----------------------------------- -----------------------------------
  API availability                    99.5%+

  Payment reconciliation              Retry until confirmed or manually
                                      reviewed

  Critical writes                     Transactional database operations

  Evidence                            Durable storage with
                                      checksums/metadata

  Audit                               Append-only logical event history
  -----------------------------------------------------------------------
