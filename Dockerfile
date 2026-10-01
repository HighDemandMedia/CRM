FROM python:3.12-slim-bookworm AS base

# Prevent Python from buffering stdout/stderr (useful for Docker logs)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# PostgreSQL client headers; PDF rendering is maintained in the local lab.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv (fast Python package manager).
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv

# Move the venv outside of backend so it doesn't get overwritten with the copy
ENV UV_PROJECT_ENVIRONMENT=/opt/venv

# Dependency installation is separate so the runtime never installs test tools.
COPY backend/pyproject.toml backend/uv.lock backend/.python-version ./

FROM base AS development
RUN uv sync --frozen --no-install-project

# Copy backend source
COPY backend/ .
COPY LICENSE /app/LICENSE

# Put the venv's binaries on PATH so `python`, `gunicorn`, `celery` etc. resolve.
ENV PATH="/opt/venv/bin:$PATH"

# Local Compose selects the development stage and its own entrypoint.
# Hosted services run without root and never create default credentials.
FROM base AS runtime
RUN uv sync --frozen --no-install-project --no-dev
COPY backend/ .
COPY LICENSE /app/LICENSE
RUN find /app -type d -name tests -prune -exec rm -rf {} +
ENV PATH="/opt/venv/bin:$PATH"
RUN groupadd --gid 10001 crm && useradd --uid 10001 --gid crm --create-home crm \
    && chown -R crm:crm /app
USER crm

EXPOSE 8000
CMD ["sh", "bin/start-web.sh"]
