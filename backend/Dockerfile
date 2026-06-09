FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:${PATH}"

WORKDIR /app

# uv binary from official image
COPY --from=ghcr.io/astral-sh/uv:0.5.4 /uv /uvx /usr/local/bin/

# System deps (libpq for psycopg, build tools for any wheels that need it)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first for layer caching. The lock file may not exist on
# first build — uv generates it then; subsequent builds reuse it.
COPY pyproject.toml ./
COPY uv.lock* ./
RUN uv sync --all-groups --no-install-project

# Playwright browser bundle. Installed AFTER uv sync so playwright CLI exists.
# `install-deps` brings in the chromium runtime libraries; `install chromium`
# downloads the actual browser binary (~150MB). Adds ~400MB total to the image.
RUN uv run playwright install-deps chromium && \
    uv run playwright install chromium

# Project source (bind-mounted in dev; baked in for prod images)
COPY . .

EXPOSE 8000

CMD ["uv", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]
