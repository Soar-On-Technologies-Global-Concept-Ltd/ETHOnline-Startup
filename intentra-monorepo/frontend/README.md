# Intentra Frontend

This directory contains the Next.js (App Router) frontend for the Intentra platform.

## 🛠 Tech Stack
*   **Framework:** Next.js 14+ (App Router)
*   **Language:** TypeScript
*   **Styling:** Vanilla CSS (Glassmorphism & Vibrant UI focus)
*   **Authentication & Wallet:** Privy
*   **Hardware Security:** `@ledgerhq` (EIP-7730 Clear Signing)
*   **Sybil Resistance:** World ID IDKit

## 🧩 Component Philosophy
We strictly adhere to a highly modular UI component architecture:
*   **Dumb/Presentational Components:** Should purely take in props and render UI (e.g., `<QuoteCard />`, `<TransactionTimeline />`).
*   **Smart/Container Components:** Handle data fetching, state, and wallet interactions (e.g., `<LedgerClearSigner />`, `<PrivyLoginButton />`).

All reusable components must be placed in `src/components/`. 

## 🎨 UI & Styling Rules
*   **Vibrant & Glassmorphism:** The UI must feel premium, responsive, and alive. Use backdrop filters, dynamic gradients, and smooth micro-animations.
*   **Invisible Complexity:** The user should never see words like "Hedera," "Smart Contract," or "Escrow" unless necessary. The UX must feel like a Web2 shopping app while the Web3 security operates silently.

## 🚀 Getting Started

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.
