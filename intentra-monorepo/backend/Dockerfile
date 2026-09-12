FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv

RUN apt-get update && apt-get install -y --no-install-recommends libpq5 curl && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY app ./app
RUN pip install --upgrade pip && pip install .

COPY migrations ./migrations
COPY alembic.ini ./
COPY scripts ./scripts
COPY shared ./shared

EXPOSE 8000
# PORT is injected by the platform (Render, Fly, Cloud Run); 8000 is the local default.
ENV PORT=8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s CMD curl -fsS http://localhost:${PORT}/healthz || exit 1
CMD ["sh", "scripts/start.sh"]
