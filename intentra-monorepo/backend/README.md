# Intentra Backend

This directory contains the FastAPI backend for the Intentra platform.

## 🛠 Tech Stack
*   **Framework:** FastAPI (Python 3.10+)
*   **Database ORM:** SQLModel (SQLAlchemy)
*   **Database Engine:** PostgreSQL via asyncpg
*   **Task Queue:** Celery & Redis
*   **External Integrations:** Hedera Python SDK, Moove API, Bazantic MCP, World ID REST API.

## 📐 Clean Architecture Rules

We strictly enforce a Modular Monolith structure using Clean Architecture principles.

*   **`src/domain/`**: Contains only SQLModel database entities and pure Pydantic schemas. NO business logic.
*   **`src/use_cases/`**: Contains the core business logic (e.g., `PaymentService`, `IntentManager`). This layer can touch the database and external APIs.
*   **`src/entrypoints/`**: Contains the FastAPI routers. **CRITICAL RULE:** Entrypoints cannot directly talk to the database. They must instantiate a Use Case class and call its methods.

## 🚀 Getting Started

1. **Activate the Virtual Environment:**
```bash
source venv/bin/activate
```

2. **Run Migrations (Alembic):**
*(Ensure your postgres docker container is running)*
```bash
alembic upgrade head
```

3. **Start the API Server:**
```bash
uvicorn src.entrypoints.api:app --reload
```

## ⚙️ Celery Background Workers

The Moove API integration requires background polling to check if a virtual card transaction was successful. 
To start the Celery worker (requires Redis):

```bash
celery -A src.use_cases.celery_worker worker --loglevel=info
```
