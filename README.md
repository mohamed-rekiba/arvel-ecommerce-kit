# arvel-ecommerce-kit

A complete e-commerce application built on the **arvel** framework — the proof app that exercises
every framework capability (auth, ORM + media library, cart/checkout, payments, queues, scheduler,
OIDC admin, observability) through the real consumer path. Catalog + admin are Vue SPAs against the
arvel REST API.

## Quick start

```bash
# 1. arvel isn't on PyPI yet — clone it as a sibling, then install
#    (this kit's pyproject points at ../arvel)
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
at a throwaway sqlite file so it needs no containers. Integration tests against real services live
in arvel's own `tests/integration` (testcontainers).

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

## API docs (OpenAPI)

With the server running, interactive docs are at **http://127.0.0.1:8000/docs** (raw document at
`/docs/openapi.json`). Handlers are typed with `arvel.Schema`, so request/response schemas + operation
descriptions (from docstrings) generate automatically. Configure in `config/openapi.py`.

## Structure

```
bootstrap/        configure + build the app (routing, providers, middlewares, config)
config/           configuration (loaded via config("..."))
routes/           web.py · api.py · console.py
app/              models · controllers · services · policies · jobs · listeners · mail · events · auth
database/         migrations · seeders · factories
storefront/       Vue 3 SPA (catalog) — `cd storefront && npm install && npm run dev`
docker-compose.yml  Postgres · Valkey · RabbitMQ · RustFS (S3) · Keycloak (OIDC) · Mailpit
```
