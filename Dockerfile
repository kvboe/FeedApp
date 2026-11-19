# ---- 1. Build the React frontend -------------------------------------------
# The built files are plain HTML/JS/CSS, the same for every CPU, so this stage
# runs on the build machine's own platform (no emulation in multi-arch builds).
FROM --platform=$BUILDPLATFORM node:22-alpine AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---- 2. Python dependencies, installed with uv --------------------------------
# Same base as the final stage, so the virtualenv's interpreter path and the
# musl wheels match. Only the finished .venv is copied out; uv itself is not shipped.
FROM python:3.12-alpine AS python-deps
COPY --from=ghcr.io/astral-sh/uv:0.13.9 /uv /bin/uv
ENV UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0 UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project \
 && find /app/.venv -name __pycache__ -prune -exec rm -rf {} +

# ---- 3. Runtime: Python API + static hosting --------------------------------
FROM python:3.12-alpine

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/app/.venv/bin:$PATH \
    DB_PATH=/data/feedapp.db

COPY --from=python-deps /app/.venv /app/.venv
COPY app /app/app
COPY --from=frontend /frontend/dist /app/frontend/dist

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
