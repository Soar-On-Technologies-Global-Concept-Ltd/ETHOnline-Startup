# Intentra — ETHOnline 2026 Submission

> **AI can find a provider and prepare a payment. It cannot create authority. Pay is not proof of work. A complaint is not a verdict.**

Intentra ties every payment to what a person actually authorized and to what was actually delivered. It is an AI-powered service marketplace secured by cryptographic signatures, human verification, and a trustless Escrow smart contract.

---

##  The Problem

In Nigeria, people pay artisans and small service providers up front, usually by bank transfer, and hope for the best. When a job is incomplete, there is no record of what was agreed, no verifiable evidence, and no fair way to settle it. As AI agents start finding and booking services on behalf of users, this gets worse: an agent can complete a payment in seconds, but payment completion does not prove the work was done.

##  The Solution

Intentra introduces three missing layers to AI commerce:
1. **Immutable Authority:** Users sign an EIP-712 Mandate from an embedded wallet. The AI proposes, the human signs.
2. **Cryptographic Evidence:** Work delivery photos are hashed and anchored on-chain.
3. **Trustless Escrow:** Funds are locked in a USDC smart contract on the Arc network. Neither the buyer nor the seller controls the money until the job is confirmed or an AI-mediated dispute resolution is signed by both parties.

---

##  The Demo Flow (The "Surulere Painter")

Our hackathon demo walks through a single, end-to-end accountable transaction:

1. **Sign In:** The user logs in via Email. Privy creates a frictionless embedded wallet in the background.
2. **Intent:** The user types: *"Paint a 2-bedroom in Surulere under ₦180k this Saturday."* The AI parses this into a structured schema.
3. **Recommendation:** The system deterministically ranks providers and the AI explains the trade-offs.
4. **Approval & Selfie Check:** The user reviews the scope, completes a **World Selfie Check**, and signs the EIP-712 Mandate.
5. **Funding:** The user's wallet deposits USDC into the Arc Escrow Contract.
6. **Delivery:** The painter uploads after-photos, which are hashed and anchored on Arc.
7. **Dispute (The Twist):** The customer files a complaint (*"Second bedroom has one coat"*) verified by another Selfie Check. Funds are instantly frozen on-chain.
8. **Resolution:** The AI acts as an L2 arbitrator, proposing a 70/30 split citing specific evidence hashes. Both parties sign the resolution, and the Smart Contract executes the split.

---

## 🏗️ Architecture (The 3 Pillars)

Intentra is built on a strict separation of concerns to ensure funds are never at risk:

*   **Frontend (Bun / TypeScript):** An untrusted client. It collects World Selfie Checks and generates cryptographic signatures via Privy.
*   **Backend (FastAPI / Python):** The trusted workflow orchestrator. It handles AI logic, state transitions, and holds the "Resolver Key" to anchor evidence and execute mutually-signed dispute splits. It never holds funds.
*   **Smart Contract (Solidity):** Deployed to the **Arc Testnet**. The ultimate vault. It enforces the rules mathematically—funds can only move to the customer or provider.

---

## 🤝 Partner Technologies Used

*   **Arc (Primary Settlement):** Our `IntentraEscrow.sol` contract is deployed on the Arc testnet. It acts as a conditional, multi-step settlement engine utilizing USDC.
*   **The Graph:** Used by our AI Agent to retrieve live on-chain trust scores for providers by querying `EvidenceAnchored` and `DisputeOpened` events on the Arc testnet. This is a core data source before AI makes any recommendations.
*   **Privy:** Frictionless onboarding via email login and embedded wallets. Used to cryptographically sign EIP-712 Mandates and Resolutions without exposing seed phrases or gas fees.
*   **World (Selfie Check):** Used as a Sybil-resistant risk signal at the two most critical moments: Approving a payment, and filing a dispute (preventing bots from freezing provider funds).

---

## 🎯 Hackathon Scope: What We Built
Given the 48-hour timeframe, we ruthlessly scoped the MVP to prove the core concept (The Trust Engine).

**Frontend Scope:**
*   `app/page.tsx`: Public Landing Page.
*   `app/dashboard/consumer/page.tsx`: Consumer Intent Input.
*   `app/intent/[id]/page.tsx`: The Transaction Hub (Quote, Trust Score, Approval, Evidence Upload).
*(Note: Full Provider and Business analytics dashboards are deferred post-hackathon).*

**Backend Scope:**
*   FastAPI Modular Monolith.
*   `AgentService`: AI negotiation and parsing.
*   `TrustService`: The Graph integration for on-chain scores.
*   `PaymentService`: Arc testnet smart contract execution.

---

## 💻 Running Locally

### Prerequisites
*   [Bun](https://bun.sh/) (Frontend)
*   Python 3.11+ (Backend)
*   Docker (PostgreSQL)

### Setup
1. Clone the repository and navigate to the monorepo root.
2. Run `docker-compose up -d` to start the database.
3. **Backend:** Navigate to `/backend`, create a `.env`, and run `fastapi dev app/main.py`.
4. **Frontend:** Navigate to `/frontend`, run `bun install`, and `bun dev`.

---

## 🛠️ Contributing & Pull Requests (Hackathon Devs)

**CRITICAL INSTRUCTION FOR DEVELOPERS:**
*   **DO NOT** push or create Pull Requests against the `main` branch.
*   All feature branches must be PR'd into the **`staging`** branch.
*   The `main` branch is strictly reserved for the final, verified hackathon submission at the end of the 48 hours.

**How to start your work:**
```bash
git fetch origin
git checkout staging
git pull origin staging
git checkout -b feature/your-feature-name
```
