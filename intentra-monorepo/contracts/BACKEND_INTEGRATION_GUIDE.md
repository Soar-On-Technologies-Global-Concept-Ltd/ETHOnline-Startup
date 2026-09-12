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

When testing locally or on Arc testnet, you can run the deployment script:
```bash
cd intentra-monorepo/contracts
forge script script/Deploy.s.sol --rpc-url <URL> --broadcast
```

This will deploy a `MockUSDC` token and the `IntentraEscrow` contract. Ensure your backend `.env` variables point to these newly generated addresses.
