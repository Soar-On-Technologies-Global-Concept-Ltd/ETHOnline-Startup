# Intentra: Repository & UI Development Guide

This document outlines how the Intentra monorepo should be scaffolded, what the README files should contain, and a complete breakdown of the modular UI components required for the Next.js frontend.

---

## 1. Monorepo Scaffolding & Directory Structure

To ensure maximum maintainability, we will use a strict **Monorepo** structure. 

```text
intentra-monorepo/
│
├── frontend/                 # Next.js App Router (React)
│   ├── src/
│   │   ├── app/              # Next.js Pages & Routing
│   │   ├── components/       # Reusable UI Components
│   │   ├── hooks/            # Custom React Hooks (e.g., usePrivy, useLedger)
│   │   └── lib/              # Utility functions and API clients
│   └── README.md             # Frontend-specific documentation
│
├── backend/                  # FastAPI (Python)
│   ├── src/
│   │   ├── entrypoints/      # API Routers (e.g., /v1/intents)
│   │   ├── use_cases/        # Business Logic (e.g., PaymentService)
│   │   └── domain/           # SQLModel Database Entities
│   ├── tests/                # Pytest suite
│   └── README.md             # Backend-specific documentation
│
├── docker-compose.yml        # Local infrastructure (PostgreSQL, Redis)
└── README.md                 # Root Monorepo README
```

---

## 2. README Documentation Guidelines

### Root `README.md`
The root README is for **onboarding new developers**. It must contain:
1.  **Project Overview:** "Intentra is an AI-native transaction assurance platform..."
2.  **Architecture Diagram:** Embed the system sequence diagram.
3.  **Quickstart Guide:** The single command needed to spin up the entire stack locally (e.g., `docker-compose up -d` followed by `npm run dev` and `uvicorn run`).
4.  **Environment Variables:** A template of required API keys (Privy, World ID, Hedera, Moove, Bazantic).

### `frontend/README.md`
This README is for **UI Engineers**. It must contain:
1.  **Tech Stack:** Next.js (App Router), Vanilla CSS (or Tailwind if adopted later), Privy (Auth), `@ledgerhq` (Hardware signing).
2.  **Component Philosophy:** Explanation of strict modularity (separating Dumb/Presentational components from Smart/Data-fetching components).
3.  **State Management:** How global state (like user authentication) is handled.

### `backend/README.md`
This README is for **Backend & Data Engineers**. It must contain:
1.  **Tech Stack:** FastAPI, SQLModel, Celery, Redis, asyncpg.
2.  **Clean Architecture Rules:** Strict warnings that `entrypoints` cannot directly talk to the database without going through `use_cases`.
3.  **Database Migrations:** How to run Alembic to update the PostgreSQL schema.
4.  **Celery Workers:** How to start the background polling workers for Moove webhooks.

---

## 3. UI Requirements: Modularity & Components

To build the front end quickly and keep the codebase clean, we will heavily rely on reusable, modular React components.

### Core Pages (Next.js App Router)
*   `app/page.tsx`: **Public Landing Page.** Explains the "Trust Engine" concept.
*   `app/dashboard/consumer/page.tsx`: **Consumer Home.** Where buyers type natural language requests.
*   `app/dashboard/provider/page.tsx`: **Provider Home.** Where merchants manage jobs and upload evidence.
*   `app/dashboard/business/page.tsx`: **Business Home.** For team-based procurement and analytics.
*   `app/intent/[id]/page.tsx`: **The Transaction Hub.** The most important page; displays the Quote, the Trust Score, and the Authorization buttons.

### Reusable UI Components (`src/components/`)

We will build these as highly modular, isolated components so they can be dropped into any page.

#### 1. Security & Identity Components
*   `<PrivyLoginButton />`: Wraps the Privy SDK to handle email/wallet login and session management.
*   `<WorldIDVerifier />`: The client-side widget that connects to the World App for Sybil-resistance. Emits the `nullifier` to the parent component.
*   `<LedgerClearSigner />`: The high-security Web3 component. Renders the EIP-7730 payload and triggers the USB/Bluetooth connection to the physical Ledger device.

#### 2. Commerce & Trust Components
*   `<IntentChatBox />`: A chat-like UI where the user converses with the AI to refine their intent (e.g., setting the budget and objective constraints).
*   `<TrustScoreBadge score={95} />`: A visual indicator (Green/Yellow/Red) that displays the provider's reputation pulled from **The Graph**.
*   `<QuoteCard />`: Displays the final AI-negotiated price, timeline, and terms before approval.
*   `<TransactionTimeline status="LOCKED" />`: A visual stepper showing the lifecycle (Created → Escrow Locked → Fulfilling → Evidence Submitted → Completed).

#### 3. Operations Components
*   `<EvidenceUploader />`: A drag-and-drop component for providers to upload photos/documents of completed work.
*   `<DisputeResolver />`: The UI for filing a complaint, interacting with the GenLayer AI adjudicator, and accepting/rejecting refunds.

### UI Styling Philosophy
As requested in your initial system design:
*   **Vibrant & Glassmorphism:** The UI must not look boring. It needs to feel premium, responsive, and alive, using smooth micro-animations.
*   **Invisible Complexity:** The user should never see words like "Hedera," "Smart Contract," or "Escrow" unless necessary. The UI must feel exactly like shopping on Web2 (Amazon/Uber), with the Web3 security operating silently in the background.
