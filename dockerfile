# ---- base image ----
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS base

WORKDIR /app
ENV UV_SYSTEM_PYTHON=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src

ENV DB_PATH=/data/conversation.db

# ---- dependencies ----
COPY pyproject.toml .
RUN uv sync --no-cache

# ---- app ----
COPY app.py ./app.py
COPY src ./src

# ---- run ----
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD curl -f http://localhost:8000/health || exit 1
ENV PORT=8000
CMD ["sh", "-c", "uv run uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]