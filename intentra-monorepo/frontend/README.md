# Intentra Frontend

This directory contains the Next.js (App Router) frontend for the Intentra platform.

## 🛠 Tech Stack
*   **Framework:** Next.js 14+ (App Router)
*   **Language:** TypeScript
*   **Styling:** Vanilla CSS (Glassmorphism & Vibrant UI focus)
*   **Authentication & Wallet:** Privy

*   **Sybil Resistance:** World ID IDKit

## 🧩 Component Philosophy
We strictly adhere to a highly modular UI component architecture:
*   **Dumb/Presentational Components:** Should purely take in props and render UI (e.g., `<QuoteCard />`, `<TransactionTimeline />`).
*   **Smart/Container Components:** Handle data fetching, state, and wallet interactions (e.g., `<PrivyLoginButton />`).

All reusable components must be placed in `src/components/`. 

## 🎨 UI & Styling Rules
*   **Vibrant & Glassmorphism:** The UI must feel premium, responsive, and alive. Use backdrop filters, dynamic gradients, and smooth micro-animations.
*   **Invisible Complexity:** The user should never see words like "Arc," "Smart Contract," or "Escrow" unless necessary. The UX must feel like a Web2 shopping app while the Web3 security operates silently.

## 🚀 Getting Started

```bash
bun install
bun dev
```

## 🏗️ What to Build: Pages & Components

### Core Pages (Hackathon Scope)
*   `app/page.tsx`: **Public Landing Page.** Explains the "Trust Engine" concept.
*   `app/dashboard/consumer/page.tsx`: **Consumer Home.** Where buyers type natural language requests.
*   `app/intent/[id]/page.tsx`: **The Transaction Hub.** The most important page; displays the Quote, the Trust Score, and the Authorization buttons.
*(Note: The full Provider and Business dashboards are deferred to post-hackathon. For the demo, the provider will just use a direct link to upload evidence on the Intent page).*

### Reusable UI Components (`src/components/`)
*   `<PrivyLoginButton />`: Wraps the Privy SDK to handle email/wallet login.
*   `<WorldIDVerifier />`: The client-side widget that connects to the World App for Sybil-resistance.
*   `<IntentChatBox />`: A chat-like UI where the user converses with the AI to refine their intent.
*   `<TrustScoreBadge score={95} />`: A visual indicator (Green/Yellow/Red) that displays the provider's reputation pulled from **The Graph**.
*   `<QuoteCard />`: Displays the final AI-negotiated price, timeline, and terms before approval.
*   `<TransactionTimeline status="LOCKED" />`: A visual stepper showing the lifecycle.
*   `<EvidenceUploader />`: A drag-and-drop component for providers to upload photos/documents of completed work.
*   `<DisputeResolver />`: The UI for filing a complaint.

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.
