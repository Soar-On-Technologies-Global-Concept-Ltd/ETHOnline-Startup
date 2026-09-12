# Intentra Backend Integration Guide

This document outlines the canonical Web3 smart contract architecture for the **Intentra MVP**. It serves as a guide for backend developers to integrate their systems with the `IntentraEscrow.sol` smart contract.

## 1. The Canonical Smart Contract

The official, tested, and audited smart contract lives in `intentra-monorepo/contracts/src/IntentraEscrow.sol`. 

> **CRITICAL:** Any Solidity files located in `intentra-monorepo/backend/contracts/` (e.g., from PR #2) are obsolete and must be deleted. They do not adhere to the 2-of-3 multisig specification, lack the required timelocks, and fail to implement the human appeal escalation mechanisms.

Please use the generated ABI and TypeScript definitions located in:
`intentra-monorepo/contracts/exports/intentra-contracts.ts`

## 2. Core Integration Differences (Backend Action Required)

If you are migrating from the initial backend scaffold (PR #2), you must update your FastAPI state machine, models, and integrations to align with the canonical Web3 contract:

### 2.1 State Machine
Your database enum and state logic must map to these strict on-chain states:
1. `AWAITING_FUNDS` (0)
2. `FUNDED` (1)
3. `IN_DISPUTE` (2)
4. `TIMELOCKED` (3)
5. `APPEALED` (4)
6. `RESOLVED` (5)

### 2.2 Identifier
The contract uses an auto-incrementing `uint256 intentId` to identify jobs, **not** a `bytes32 txKey`. Your backend must listen for the `IntentCreated` event to capture this `intentId` and map it to your internal UUIDs.

### 2.3 2-of-3 Multisig & EIP-712
To resolve a transaction off-chain via signatures, the contract requires **two distinct signatures** from the set `{Customer, Provider, AI_Arbitrator}`. 
* The typed data structure is named `ResolveIntent`, not `Resolution`.
* It expects exact amounts (`customerAmount`, `providerAmount` in 6-decimal USDC), **not** basis points (`providerBps`). 

The correct EIP-712 signature format is:
```typescript
const RESOLUTION_TYPES = {
  ResolveIntent: [
    { name: "intentId", type: "uint256" },
    { name: "customerAmount", type: "uint256" },
    { name: "providerAmount", type: "uint256" }
  ]
};
```

### 2.4 Timeouts and Escalations (New Backend Logic Required)
Your backend background workers (Celery/Cron) must be aware of the following on-chain timeouts:
* **14-Day Abandonment (`executeAbandonment`)**: If an intent sits in `FUNDED` or `IN_DISPUTE` for 14 days, anyone can call this to force execution.
* **48-Hour AI Timelock (`submitAIProposal`)**: When the backend AI submits a proposal, the intent becomes `TIMELOCKED`. No execution can happen for 48 hours.
* **Human Appeal (`escalateAppeal`)**: During the 48-hour window, users can pay a native ETH fee to escalate the dispute to `APPEALED`. The funds are frozen indefinitely until an Admin calls `resolveHumanAppeal`.

## 3. Deployment & Addresses

The smart contracts are currently deployed live on the **Arc Testnet** (Chain ID: `5042002`).

*   **Mock USDC Token (6 Decimals):** `0xFa5a5744898B71c93fF80F179d95184864143190`
*   **IntentraEscrow Contract:** `0xeF3a099CC877F6e274b037847A6ee44C4d62648D`

These addresses and the full ABI are exported in `intentra-monorepo/contracts/exports/intentra-contracts.ts`. Ensure your backend `.env` variables and the Graph subgraphs are pointing to these live addresses.

For instructions on how to deploy or interact with the contract using a MetaMask account, please refer to the `README.md` file in this directory.

## 4. Smart Contract API Reference (Endpoints & Events)

To fully integrate the backend, your `web3.py` service must interact with the following endpoints (functions) and listen to the following events.

### Core Write Functions (Transactions)
*   `createIntent(address provider, address token, uint256 amount)`: Initializes a new job.
*   `fundIntent(uint256 intentId)`: Locks the USDC in escrow (Customer must call `usdc.approve()` first).
*   `raiseDispute(uint256 intentId)`: Moves state from `FUNDED` to `IN_DISPUTE`.
*   `submitAIProposal(uint256 intentId, uint256 customerAmount, uint256 providerAmount)`: **[AI ARBITRATOR ONLY]** Submits a resolution and starts the 48-hour timelock.
*   `executeWithSignatures(uint256 intentId, uint256 customerAmount, uint256 providerAmount, bytes sigA, bytes sigB)`: Resolves the intent immediately if 2-of-3 signatures are valid.
*   `escalateAppeal(uint256 intentId)`: **[PAYABLE]** Escalates an AI proposal to a human during the 48-hour timelock by staking native ETH.
*   `resolveHumanAppeal(uint256 intentId, uint256 customerAmount, uint256 providerAmount)`: **[OWNER ONLY]** Concludes an escalated dispute.
*   `executeAbandonment(uint256 intentId)`: Forces resolution if no action has been taken for 14 days.

### Core Read Functions (Views)
*   `getIntent(uint256 intentId)`: Returns the full `Intent` struct containing the state, amounts, and participants.
*   `getProposal(uint256 intentId)`: Returns the active `Proposal` struct (who proposed it, amounts, and timestamp).

### Events to Listen For (The Graph / Webhooks)
Your backend should index these events to trigger state changes in your database:
*   `IntentCreated(uint256 indexed intentId, address indexed customer, address indexed provider, address token, uint256 amount)`
*   `IntentFunded(uint256 indexed intentId, uint256 amount)`
*   `DisputeRaised(uint256 indexed intentId, address indexed raisedBy)`
*   `AIProposalSubmitted(uint256 indexed intentId, uint256 customerAmount, uint256 providerAmount)`
*   `AppealEscalated(uint256 indexed intentId, address indexed appellant, uint256 stake)`
*   `IntentResolved(uint256 indexed intentId, uint256 customerAmount, uint256 providerAmount)`
*   `AbandonmentExecuted(uint256 indexed intentId, address indexed triggeredBy)`
