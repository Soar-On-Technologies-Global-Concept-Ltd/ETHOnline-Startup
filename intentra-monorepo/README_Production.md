# Intentra: The Trust Engine for Agentic Commerce

Intentra is an AI-native transaction assurance platform. As AI agents increasingly act on behalf of users, the primary bottleneck is no longer discovery—it's **outcome assurance**. 

Intentra sits between AI agents and service providers, holding funds in an Arc escrow smart contract until cryptographic proof of fulfillment is submitted and verified. 

## 🏗 System Architecture Overview

*   **Frontend:** Next.js (App Router), Privy.
*   **Backend:** FastAPI (Modular Monolith / Clean Architecture), SQLModel.
*   **Infrastructure:** PostgreSQL, Redis, Celery (for async webhook polling).
*   **Protocols Integrated:** Arc, Bazantic (MCP), Moove (VCC), World ID, The Graph.

## 🚀 Quickstart Guide

To spin up the entire Intentra stack locally:

1.  **Start Infrastructure:**
    ```bash
    cd intentra-monorepo
    docker-compose up -d
    ```

2.  **Start the Backend (FastAPI):**
    ```bash
    cd backend
    source venv/bin/activate
    uvicorn src.entrypoints.api:app --reload
    ```
    *(Note: You'll also need to start the Celery worker for Moove webhooks if testing payments).*

3.  **Start the Frontend (Next.js):**
    ```bash
    cd frontend
    bun install
    bun dev
    ```

## 🔑 Environment Variables

You will need a `.env` file in both the `frontend` and `backend` directories.

**Backend (`backend/.env`):**
```env
DATABASE_URL=postgresql+asyncpg://intentra:intentra_password@localhost:5432/intentradb
REDIS_URL=redis://localhost:6379/0
ARC_NETWORK=testnet
ARC_ACCOUNT_ID=0.0.xxxxx
ARC_PRIVATE_KEY=xxxxxxxxxxxxxxxxx
MOOVE_API_KEY=moove_test_key
BAZANTIC_API_KEY=bazantic_test_key
WORLD_APP_ID=app_staging_xxxxxxxx
```

**Frontend (`frontend/.env.local`):**
```env
NEXT_PUBLIC_PRIVY_APP_ID=your_privy_app_id
NEXT_PUBLIC_WORLD_APP_ID=app_staging_xxxxxxxx
```
