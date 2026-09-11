**Intentra --- Moove Integration Specification**

*Intentra*

Version: September 2026

# 1. Purpose

Define the first production integration between Intentra and Moove
Agentic Payments without assuming undocumented Moove capabilities.

# 2. Initial Moove Scope

-   Moove Receive Agent

-   Payment-link creation

-   Payment-link retrieval/reconciliation

-   Server-side API authentication

-   Association of Moove payment records with Intentra transaction
    records

# 3. Integration Boundary

Moove is the payment/settlement layer. Intentra remains responsible for
user intent, authorization, agreement, fulfillment, evidence, outcome
and resolution.

# 4. Payment Flow

1.  Intentra creates an authorized transaction.

2.  Intentra validates amount, currency, provider and policy.

3.  Backend calls the Moove payment-link API.

4.  Intentra stores the Moove payment-link ID.

5.  User completes payment through the Moove checkout flow.

6.  Intentra reconciles payment status using the Moove API.

7.  Intentra advances the transaction only after the payment state is
    verified.

# 5. Security

-   Keep API credentials only on the server.

-   Use least-privilege scopes.

-   Never expose credentials to the model or browser.

-   Validate all amounts against the stored agreement.

-   Use idempotency for payment creation where supported by the
    integration layer.

-   Log every payment request and reconciliation result.

# 6. Current Documentation Constraints

The current public Moove documentation should be treated as the source
of truth for the available Agentic Payments surface. The initial design
should not depend on Send, Swap, Bridge or Ramp capabilities until those
APIs are actually available to the project.

# 7. Future Expansion

-   Additional Moove agents as they become available

-   More autonomous payment flows

-   Expanded settlement workflows

-   Agent-to-agent payment scenarios

# 8. Product Message

Moove moves the money; Intentra makes the transaction accountable.
