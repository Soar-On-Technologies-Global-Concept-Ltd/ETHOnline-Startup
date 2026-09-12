#!/bin/sh
# Container entrypoint. Migrations first, then optionally the demo seed, then the API.
#
# SEED_DEMO_DATA=true exists because a managed platform hands you an empty database and, on a free plan, no shell
# to seed it from. scripts/seed.py is idempotent — it matches providers by email and skips transaction keys it has
# already written — so running it on every boot is safe.
set -e

alembic upgrade head

if [ "${SEED_DEMO_DATA}" = "true" ]; then
  echo "seeding demo providers"
  python scripts/seed.py || echo "WARNING: seeding failed — the provider list will be empty"
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers
