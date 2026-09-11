# Third-Party Integration Research Notes

This document summarizes deep research into the developer documentation for each of the selected ETHOnline partner integrations. It outlines how each technology works and how we will integrate it into the **Intentra** stack (NestJS backend, React/Vite frontend).

## 1. Privy (Authentication & Wallets)
Privy is a comprehensive toolkit for Web3 authentication. For Intentra, Privy acts as our primary authorization layer and policy enforcer.
*   **Integration (Frontend):** We will use the `@privy-io/react-auth` SDK to wrap our React app in a `<PrivyProvider>`. This allows users to log in via email, social, or external wallets (MetaMask).
*   **Integration (Backend):** We will use the official server-side Python SDK provided by Privy in our FastAPI backend to verify OIDC/JWKS authentication tokens attached to API requests and manage user profiles.
*   **Agent Wallets:** Privy supports provisioning non-custodial **embedded wallets**, which can be tied to the AI agent. The agent can use this wallet, but policies will dictate transaction limits.

## 2. Hedera (Payment Rail & Agent Tools)
Hedera will serve as the actual settlement network for our hackathon-specific crypto payment rail, utilizing HBAR (the native currency).
*   **Integration (Backend):** We will use the officially recognized community SDK `hiero-sdk-python` for core network execution in our FastAPI backend.
*   **Agent Toolkit:** We will utilize the `hedera-agent-kit` with LangChain. This allows our internal agents to use plugins like `core_account_plugin` to execute HBAR transfers and query balances.
*   **Human-in-the-Loop Execution:** The `hedera-agent-kit` supports `AgentMode.RETURN_BYTES`. This is a massive security feature for Intentra: the AI agent can formulate a transaction, return the raw bytes, and Intentra passes those bytes to the frontend for the user to securely sign (e.g., via Ledger clear signing) before execution.

## 3. World ID (Human Verification)
World ID (formerly Worldcoin) proves that the actor is a unique human, preventing Sybil attacks or unauthorized agent looping.
*   **Integration (Backend):** With the latest **World ID 4.0**, we must implement **RP (Relying Party) Signatures** on the backend to prevent impersonation. The FastAPI backend will then forward the proof payload to World's `/v4/verify/{rp_id}` REST API.
*   **Data Model Constraints:** The backend must store the unique proof **nullifier** in the PostgreSQL database as a `NUMERIC(78, 0)` to securely represent the 256-bit integer and prevent double-verifications.

## 4. Ledger (Clear Signing & Security)
Ledger enforces hardware security for high-risk, irreversible actions. We want to implement **Clear Signing** (ERC-7730) so users see exactly what they are approving, rather than blind hex strings.
*   **Integration (Frontend):** We will use the `@ledgerhq/ledger-wallet-provider-evm` web component SDK to initialize an EIP-1193 provider (`initializeLedgerProvider`). This automatically handles the UI, USB/Bluetooth transport, and enables Clear Signing out of the box.
*   **Custom Descriptors:** To support Intentra-specific transactions, we will need to create an ERC-7730 JSON metadata file that maps our smart contract/transaction fields to human-readable text (e.g., "Pay Provider", "Amount: 150"). This ensures the user's hardware device explicitly shows the action the AI is attempting to take.

## 5. The Graph (On-chain Evidence)
The Graph indexes blockchain data, providing an immutable source of truth for transaction history and provider reputation.
*   **Integration:** We will use standard HTTP requests (via `httpx`) for simple queries, or the `subgrounds` Python library for more complex, Pythonic GraphQL querying. 
*   **AI Agent Integration:** The Graph provides a `Subgraph MCP (Model Context Protocol)` server. We can use this to allow our internal AI agents to query subgraph data using natural language, seamlessly translating prompts into GraphQL queries.
*   **Execution:** Intentra will dynamically retrieve a provider's past on-chain fulfillment history and use it as "Trust" evidence during the recommendation phase.

## 6. Bazantic (Agent API Gateway)
Bazantic turns standard APIs into services that AI agents can use and pay for (via x402/MPP Gateways and MCP Servers).
*   **Integration:** Intentra will define a complete OpenAPI 3.1 specification via our FastAPI backend. We will deploy this specification to Bazantic as a new "agent gateway".
*   **Execution:** Bazantic will automatically provision an MCP (Model Context Protocol) server and an x402/MPP payment pathway for Intentra. External AI agents can then discover Intentra's API, negotiate prices, and pay for transaction assurance directly through the Bazantic gateway (e.g., using `baz curl` or an MCP client).

## 7. Moove (Agentic Payments Developer Program)
Moove has launched a developer fund specifically for "agentic payments".
*   **Integration:** Intentra will use the **Moove Receive Agent** capabilities (via standard REST API to `MOOVE_API_BASE_URL`). 
*   **Execution:** When a transaction reaches the "Payment" state, the backend will call `POST /v1/payment-link`. 
    *   **Crucial Constraints:** The `toAmount` must be passed as a string (e.g., `"250.00"`), and we will set `description` to our internal Intentra Transaction ID for reconciliation.
    *   **Reconciliation:** We will run a Celery background task to politely poll `GET /v1/payment-link/{id}` until the status is `completed`, at which point the Intentra transaction moves to the `FULFILLING` state.
