# Intentra Smart Contracts

This directory contains the core smart contracts for the Intentra MVP. 

## Network
**Target Network:** Arc Testnet (Chain ID: `5042002`)

### Live Deployments (Arc Testnet)
*   **IntentraEscrow:** `0xeF3a099CC877F6e274b037847A6ee44C4d62648D`
*   **Mock USDC:** `0xFa5a5744898B71c93fF80F179d95184864143190`

## Deployment Guide (Using MetaMask)

If you want to deploy the `IntentraEscrow.sol` contract using a MetaMask account, follow these steps. We will use Foundry's encrypted keystore to avoid leaving private keys in plaintext `.env` files.

### 1. Export your Private Key from MetaMask
1. Open MetaMask.
2. Click the three dots next to your account name -> Account Details -> Show Private Key.
3. Copy the private key (do not share this!).

### 2. Import into Foundry's Secure Keystore
In your terminal, navigate to this `contracts/` folder and run:

```bash
cast wallet import deployer --interactive
```
* When prompted, paste your MetaMask private key.
* Create a strong password to encrypt the keystore on your machine.

### 3. Set Environment Variables
Create a `.env` file in this directory (`intentra-monorepo/contracts/.env`) with the following contents:

```env
ARC_RPC_URL=https://<insert-arc-testnet-rpc-url-here>
AI_ARBITRATOR=<insert-your-backend-ai-wallet-address>
OWNER=<insert-your-metamask-address>
APPEAL_FEE=10000000000000000 # 0.01 ether (in wei)
# USDC_ADDRESS=<insert-arc-usdc-address-if-known>
```
*(Note: If you leave `USDC_ADDRESS` blank, the script will deploy a `MockUSDC` token for you to test with).*

### 4. Deploy to Arc Testnet
Load your `.env` variables and run the deployment script, using the `--account deployer` flag to sign the transaction with your encrypted MetaMask keystore:

```bash
source .env
forge script script/Deploy.s.sol --rpc-url arc_testnet --account deployer --broadcast
```

* Foundry will prompt you for the password you created in step 2.
* Once complete, it will print out the deployed `IntentraEscrow` address and `MockUSDC` address.

### 5. Update the Backend
Copy the deployed contract address and paste it into `exports/intentra-contracts.ts` (the `INTENTRA_ESCROW_ADDRESS` constant). The backend developers will use this file to interact with your newly deployed smart contract.
