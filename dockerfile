# ---- base image ----
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS base

WORKDIR /app
ENV UV_SYSTEM_PYTHON=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# ---- dependencies ----
COPY pyproject.toml .
RUN uv sync --no-cache

# ---- app ----
COPY app.py ./app.py
COPY src ./src

# ---- run ----
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]