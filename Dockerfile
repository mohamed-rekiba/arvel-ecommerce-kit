# ---- frontend ----
FROM node:26-alpine AS frontend
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build
# /src/dist becomes ./public in the runtime image below.

# ---- backend builder (nothing here ships) ----
FROM python:3.14-slim-trixie AS backend-builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/
WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_SYSTEM_PYTHON=1

COPY pyproject.toml uv.lock ./

# No venv — single-purpose container already is the isolation boundary. arvel installs from
# PyPI, not the editable ../arvel sibling this repo's [tool.uv.sources] points dev at; --frozen
# and --no-sources can't be combined, so export everything but arvel from the lockfile, then
# install arvel by itself from the index.
RUN uv export --frozen --no-dev --no-editable --no-emit-package arvel -o requirements.txt && \
    uv pip install --system --no-cache -r requirements.txt && \
    uv pip install --system --no-cache "arvel[standard,oidc,s3,telemetry,search,queue-amqp]" && \
    rm -f /usr/local/bin/uv /usr/local/bin/uvx requirements.txt

# with_public_dir(...) (bootstrap/app.py) serves this via arvel's Route.public() — never committed.
COPY --from=frontend /src/dist/. ./public/

# ---- runtime (hardened, nonroot) ----
FROM python:3.14-slim-trixie AS backend

# Strip setuid/setgid bits, drop apt's package-list cache, add a fixed-uid nonroot account.
RUN find / -xdev -perm /6000 -type f -exec chmod a-s {} + 2>/dev/null; \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/* && \
    groupadd --gid 10001 app && \
    useradd --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app
COPY --from=backend-builder --chown=app:app /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY --from=backend-builder --chown=app:app /app/public ./public
COPY --exclude=frontend --exclude=public . /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONFAULTHANDLER=1

USER app
EXPOSE 8000
CMD ["python", "-m", "granian", "--interface", "asgi", "--host", "0.0.0.0", "--port", "8000", "asgi:asgi_app"]
