# arvel-ecommerce-kit

A complete e-commerce application built on the **arvel** framework — the proof app that exercises
every framework capability (auth, ORM + media library, cart/checkout, payments, queues, scheduler,
OIDC admin, observability) through the real consumer path. Catalog + admin are Vue SPAs against the
arvel REST API.

## Quick start

```bash
# 1. arvel IS on PyPI, but local dev tracks the framework source directly (this kit's own
#    pyproject.toml points at ../arvel, editable) — clone it as a sibling, then install.
#    (Docker doesn't need this — the image installs arvel straight from PyPI; see Docker, below.)
uv sync                              # installs arvel[standard,sqlite,postgres,telemetry,jwt,media] + dev

# 2. configuration
cp .env.example .env                 # defaults already match docker-compose.yml

# 3. infrastructure (PostgreSQL)
docker compose up -d db              # Postgres on :5432 (arvel/arvel/arvel_ecommerce_kit)

# 4. database + demo data (downloads real product images via the Http client → media library)
uv run arvel migrate
uv run arvel db:seed

# 5. run it
uv run arvel serve                   # http://127.0.0.1:8000  (API docs at /docs)
```

## Test

```bash
uv run pytest                        # the suite runs on an in-process sqlite per test (fast)
uv run pyright                       # strict type-check (app code)
```

The app runs on **PostgreSQL** (`docker compose up -d db`); the test suite points `DATABASE_URL`
at a throwaway sqlite file so it needs no containers. The kit's own real-service tier lives in
`tests/integration` (testcontainers — one smoke test per service, plus per-feature integration
tests): `make test-integration` boots throwaway Postgres/Valkey/RabbitMQ/RustFS/Meilisearch/
Keycloak/Mailpit containers and drives each arvel module through the kit's production boot.
arvel's own `tests/integration` covers the framework side.

**Queued mail & notifications.** Order mail (confirmation, shipped) and the shipped notification
are `ShouldQueue`: the request only enqueues; `make worker` (`arvel queue:work`) delivers them off
RabbitMQ — one job per channel, so an SMTP outage can only fail the mail job. A job that exhausts
its retries lands in `failed_jobs`: inspect with `uv run arvel queue:failed`, re-dispatch with
`uv run arvel queue:retry <id|all>`.

## What it demonstrates (and where)

| Capability | Where |
|---|---|
| Catalog (ORM, relations, eager-load, pagination, enum casts) | `app/controllers/catalog_controller.py` |
| Product image **gallery** (media library + thumb/preview conversions) | `app/models/product.py`, `app/services/product_image_service.py` |
| Customer auth (tokens, hashing, password reset) | `app/controllers/auth_controller.py` |
| Authorization (gates/policies, admin guards) | `app/policies/`, `app/controllers/admin_product_controller.py` |
| Cart (sessions/cache) · Checkout (transactions, events, state machine) | `cart_controller.py`, `checkout_controller.py` |
| Inventory (row locking) · Payments (Http client, idempotent webhooks) | `checkout_controller.py`, `payment_controller.py` |
| Mail · Queued jobs · Scheduler | `app/mail/`, `app/jobs/`, `app/console/` |
| Observability (telemetry spans) · Admin OIDC (Keycloak) | `checkout_controller.py`, `app/auth/admin_oidc.py` |

Walk all of it end to end on the live stack: **[docs/tour.md](docs/tour.md)** (screenshots in
`docs/screenshots/`). Maintenance mode + scheduling: [docs/operability.md](docs/operability.md).

## Docker

One production image, hardened + nonroot (`python:3.14-slim-trixie`, setuid/setgid stripped,
dedicated `app` service account — no venv, dependencies install straight into the base Python's
site-packages since the container is already the isolation boundary):

```bash
docker build -t arvel-ecommerce-kit .
docker run --rm -p 8000:8000 --env-file .env arvel-ecommerce-kit
```

Multi-stage: `frontend` builds the Vue SPA (`npm run build`), `backend-builder` resolves + installs
Python deps (arvel comes from PyPI, not the local sibling checkout `uv sync` uses for dev — see
the Dockerfile's own comments), `backend` is the shipped image. The built SPA becomes `./public`,
served by `Route.public()` (configured via `with_public_dir(...)` in `bootstrap/app.py`) — real
files served as-is, any other path falls back to `index.html` for vue-router.

## API docs (OpenAPI)

With the server running, interactive docs are at **http://127.0.0.1:8000/docs** (raw document at
`/docs/openapi.json`). Handlers are typed with `arvel.Schema`, so request/response schemas + operation
descriptions (from docstrings) generate automatically. Configure in `config/openapi.py`.

## Structure

```
bootstrap/        configure + build the app (routing, providers, middlewares, config, public/lang dirs)
config/           configuration (loaded via config("..."))
routes/           web.py · api.py · console.py
app/              models · controllers · services · policies · jobs · listeners · mail · events · auth
resources/        lang/ translations (with_lang_dir(...) in bootstrap/app.py) · views/ (Jinja2)
database/         migrations · seeders · factories
storage/app/      the "local" filesystem disk's root; storage/app/public/ is `storage:link`'s target
frontend/        Vue 3 SPA — storefront + admin (`/admin/*`, lazy chunk); `make front`
public/           NOT committed — Docker-populated from frontend/dist/, served via Route.public()
docker-compose.yml  Postgres · Valkey · RabbitMQ · RustFS (S3) · Keycloak (OIDC) · Mailpit
Dockerfile        production image (see Docker, above)
```
