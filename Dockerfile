# ---- frontend: vue-tsc + vite build ----------------------------------------
FROM node:26-alpine AS frontend
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build
# -> /src/dist: index.html + fingerprinted assets/* + favicon.ico/robots.txt/logo.* (Vite copies
# frontend/public/* verbatim into the build root) — becomes ./public in the runtime image below.

# ---- backend builder: compiles/installs deps — none of this ships -----------------------------
FROM python:3.14-slim-trixie AS backend-builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/
WORKDIR /app

# The best uv production flags
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_SYSTEM_PYTHON=1

COPY pyproject.toml uv.lock ./

# arvel is published on PyPI (0.49.0) — this repo's [tool.uv.sources] override (path = "../arvel",
# editable) is a local-dev convenience for iterating on the framework alongside the kit; the image
# doesn't need that sibling repo at all. --frozen and --no-sources can't be combined (uv rejects
# it), so: export everything else frozen from uv.lock (still fully reproducible), excluding arvel,
# then install arvel by itself straight from the index. Bump the pin here if arvel cuts a release
# this kit hasn't picked up in its own lockfile yet.
RUN uv export --frozen --no-dev --no-editable --no-emit-package arvel -o requirements.txt && \
    uv pip install --system --no-cache -r requirements.txt && \
    uv pip install --system --no-cache "arvel[standard,oidc,s3,telemetry,search,queue-amqp]==0.49.0" && \
    rm -f /usr/local/bin/uv /usr/local/bin/uvx requirements.txt

# The built SPA becomes the static doc root routes/web.py serves via Route.public() (arvel's
# Laravel-`public/`-parity static front door) — populated only here, never committed (see
# .gitignore).
COPY --from=frontend /src/dist/. ./public/

# ---- runtime: same Debian trixie/Python lineage as the builder, hardened + nonroot -------------
FROM python:3.14-slim-trixie AS backend

# Strip setuid/setgid bits (no interactive/login tooling is needed by a service container), drop
# apt's package-list cache (this stage never installs anything else), add a dedicated low-
# privilege account — a fixed, predictable uid/gid, not a real login user.
RUN find / -xdev -perm /6000 -type f -exec chmod a-s {} + 2>/dev/null; \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/* && \
    groupadd --gid 10001 app && \
    useradd --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app
COPY --from=backend-builder --chown=app:app /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY . /app
RUN rm -rf /app/frontend

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONFAULTHANDLER=1

USER app
EXPOSE 8000
CMD ["python", "-m", "granian", "--interface", "asgi", "--host", "0.0.0.0", "--port", "8000", "asgi:asgi_app"]
