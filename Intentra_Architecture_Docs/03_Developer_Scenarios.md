# Intentra: Developer Scenario Matrix

This document defines the core use cases, edge cases, and fallback flows that developers must implement when building the Intentra Monorepo. It serves as the test-case blueprint for both the Next.js frontend and FastAPI backend.

---

## 1. The "Happy Path" Scenarios

### Scenario 1.1: Standard Consumer Fiat Flow (Low Value)
*   **Actor:** Consumer (No hardware wallet).
*   **Flow:**
    1.  User logs in via **Privy** (email).
    2.  User completes **World ID** verification; backend stores the `NUMERIC(78,0)` nullifier.
    3.  User inputs: *"Hire a plumber for ₦100,000 max."*
    4.  **AgentService** finds a plumber, queries **The Graph** (returns a 95% Trust Score), and drafts a Quote.
    5.  User clicks "Approve" on the frontend.
    6.  **Privy** embedded wallet signs the transaction invisibly.
    7.  **PaymentService** detects fiat (₦) and generates a **Moove** payment link (`POST /v1/payment-link`).
    8.  **Celery** worker polls Moove until settled. Status updates to `COMPLETED`.

### Scenario 1.2: Enterprise Crypto Flow (High Value)
*   **Actor:** Organization Admin (Requires maximum security).
*   **Flow:**
    1.  External AI agent (acting for a vendor) connects to Intentra via **Bazantic** MCP Gateway and pays the x402 discovery fee.
    2.  Agent submits an Intent to charge the Organization 10,000 USDC for cloud services.
    3.  Organization Admin receives the Quote.
    4.  Admin clicks "Approve".
    6.  FastAPI receives the signature, and `ArcService` uses `web3.py` to lock 10,000 USDC in an Escrow Smart Contract.

### Scenario 1.3: External Web2 Checkout (Virtual Card Injection)
*   **Actor:** External AI Agent (e.g., Personal Shopper Bot).
*   **Flow:**
    1.  The Agent uses a headless browser (Puppeteer/Playwright) to shop on a legacy web2 site (e.g., Jumia).
    2.  Agent reaches the checkout screen but lacks a credit card.
    3.  Agent pings Intentra's **Bazantic** MCP Gateway: *"Need ₦300,000 for Jumia checkout."*
    4.  Intentra pauses the agent and asks the human user to authorize the Intent via their dashboard.
    5.  User approves the Intent via **Privy**.
    6.  Intentra backend calls the **Moove API** to instantly issue a one-time-use Virtual Credit Card (VCC) loaded with exactly ₦300,000.
    7.  Intentra securely passes the VCC details to the Agent.
    8.  The Agent injects the card details into the Jumia checkout form and completes the purchase.
---

## 2. Policy & Security Rejection Scenarios

### Scenario 2.1: World ID Sybil Attack (Duplicate Human)
*   **Trigger:** A user tries to create a second account to bypass rate limits or manipulate trust scores.
*   **System Action:** The frontend sends the World ID proof to `/v4/verify`. The backend checks the `nullifier` against the PostgreSQL database. It finds an existing `NUMERIC(78,0)` match.
*   **Result:** Backend throws a `403 Forbidden` (Duplicate Identity). Account creation/action is blocked.

### Scenario 2.2: Agent Exceeds Authorized Budget
*   **Trigger:** An external AI agent (via Bazantic) attempts to submit a Quote for $600 when the User's original Intent hard-capped the budget at $500.
*   **System Action:** The `AuthorizationService` intercepts the Quote before it is ever shown to the user.
*   **Result:** Backend rejects the payload. The Bazantic gateway returns a `400 Bad Request: Budget Exceeded` to the external agent.

### Scenario 2.3: Untrustworthy Provider
*   **Trigger:** An internal agent tries to recommend a provider, but **The Graph** subgraph query reveals the provider has a 30% completion rate and a history of disputes.
*   **System Action:** `TrustService` calculates a Trust Score of 30/100.
*   **Result:** The agent either strictly filters out this provider from the recommendations, or (if explicitly requested by the user) flags the UI with a massive red > [!WARNING] banner requiring explicit user acknowledgment of the risk.

---

## 3. Operations & Adjudication Scenarios

### Scenario 3.1: Provider Fails to Fulfill (Automatic Refund)
*   **Trigger:** Provider accepts a job but fails to upload Evidence to the `EvidenceService` before the strict deadline.
*   **System Action:** Celery background worker wakes up at the deadline timestamp.
*   **Result:** The smart contract (Arc) or pending fiat state is cancelled. Funds are automatically refunded to the Consumer. Provider's Trust Score is slashed on-chain.

### Scenario 3.2: Ambiguous Dispute (GenLayer -> Admin)
*   **Trigger:** Consumer claims the painter used the wrong color. Provider uploads photos claiming it is correct. Consumer hits "File Complaint".
*   **System Action:**
    1.  The `Transaction` is frozen (funds locked in Escrow).
    2.  Both evidence payloads (photos, chat logs) are sent to **GenLayer** (AI adjudication).
    3.  GenLayer determines the evidence is 50/50 ambiguous.
*   **Result:** The status changes to `ESCALATED`. The Intentra Admin receives an alert in the Admin Dashboard to manually review the evidence and issue a final `Resolution` (e.g., 50% partial refund).

### Scenario 3.3: Moove Webhook / Polling Failure
*   **Trigger:** User pays via the Moove link, but the Moove API goes down or the Celery worker times out after 24 hours of polling.
*   **System Action:** Celery exhausts its retry limit.
*   **Result:** Transaction status updates to `PAYMENT_UNKNOWN`. An alert is immediately fired to the Intentra DevOps team for manual reconciliation against the Moove dashboard.
