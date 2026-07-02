# The full tour — one order, end to end, on the real stack

This walkthrough exercises every major surface of the kit against the live compose stack.
It was last performed 2026-07-02; the screenshots in `docs/screenshots/s19-*.png` are from that run.

## Prerequisites

```bash
make up                      # PostgreSQL, Valkey, RabbitMQ, RustFS, Meilisearch, Keycloak, Mailpit, Grafana-LGTM
uv run arvel migrate:fresh --seed
uv run arvel search:reindex
SEARCH_DRIVER=meilisearch uv run arvel serve   # :8000
make worker                  # arvel queue:work — consumes RabbitMQ
cd frontend && npm run dev   # :5173
```

Seed a coupon (any staff bearer with `coupons.manage`):

```bash
curl -X POST localhost:8000/api/admin/coupons \
  -H "Authorization: Bearer $STAFF_TOKEN" -H 'Content-Type: application/json' \
  -d '{"code": "WELCOME10", "type": "percent", "value": 10}'
```

## 1 — Browse in French (Meilisearch + RustFS)

Open `http://localhost:5173`, switch the header toggle to **FR**. The catalog re-renders from the
locale-major translations (`Téléphone Aurora`, `Téléphones`); search hits Meilisearch in the active
locale:

```bash
curl -s 'localhost:8000/api/products?q=Téléphone' -H 'Accept-Language: fr' | jq '.data[].name'
# "Téléphone Aurora", "Téléphone Nimbus 5G"
```

The PDP gallery images are webp conversions served from RustFS (S3) — `s19-pdp-french.png`.

Switch to **AR** and the whole storefront flips **right-to-left** (`<html dir="rtl" lang="ar">` +
CSS logical properties) with Arabic chrome and catalog content (`هاتف أورورا`); the admin console
stays LTR. Arabic search rides the same Meilisearch index:

```bash
curl -s -G localhost:8000/api/products --data-urlencode 'q=أورورا' -H 'Accept-Language: ar' | jq '.data[].translation.name'
# "هاتف أورورا"
```

Evidence: `i18n-ar-catalog-rtl.png`, `i18n-ar-pdp-rtl.png`.

## 1b — v6 storefront: deals, banners, announcement (2026-07-03)

The home page is now the BestShop layout: hero **carousel** (admin-managed banners with
per-locale copy + media-library images), trust strip, **popular categories** (tiles derive their
image from a product in the subtree), **Deals of the Day** (timed flash sales with countdowns and
sell-through bars), a promo grid, and the **featured** rail. The orange **announcement bar**
surfaces the newest live coupon flagged `announce` (dismissable, per-code).

```bash
curl -s localhost:8000/api/deals | jq '.[] | {slug: .product.slug, pct: .percent_off, price: .deal_price_cents}'
curl -s localhost:8000/api/banners | jq '.[].title'
curl -s localhost:8000/api/announcement | jq .
```

**Deal prices are real**: add a deal product to the cart and the line snapshots the discounted
price; checkout re-prices every line to the price current at order time (an expired deal never
leaks into an order). Try it: open a `/deals` product, note the struck price + countdown, buy it,
and check the order subtotal. Evidence: `docs/screenshots/v6-*.png`.

## 2 — Guest cart → register → the cart follows

Add to cart as a guest (the cart rides the `X-Cart-Token` header), then create an account on
`/account`. The guest cart **merges** into the new user's cart — the badge survives sign-up.

## 3 — Coupon → checkout → pay (dev gateway + webhook + worker)

- `/cart`: apply `WELCOME10` — the summary grows a `Discount (WELCOME10) −$…` row (10%).
- `/checkout`: name + address (validated), place the order → confirmation with the full
  breakdown (`s19-order-placed.png`) and a queued **order-confirmed** email.
- Click **Pay** — the debug-only dev gateway "charges" and posts a **HMAC-signed webhook**
  back through the queue; the worker consumes it and the order flips to **PAID**
  (`s19-order-paid.png`).

## 4 — Admin over Keycloak SSO

Open `http://localhost:5173/admin` → **Continue with SSO** → the real Keycloak login
(realm `arvel`, PKCE). Sign in `admin` / `admin` → callback → dashboard
(`s19-admin-sso-dashboard.png`).

Order #1 shows lines (purchase-snapshot names), the breakdown **including the discount row**,
delivery address, the gateway charge, and the activity-trail history. Click **shipped** — the
state machine advances, the transition lands in the history, and an **order-shipped** email +
in-app notification ride the queue (`s19-admin-order-shipped.png`):

```bash
curl -s localhost:8025/api/v1/messages | jq '.messages[].Subject'
# "Your order #1 has shipped", "Your order #1 is confirmed", …
curl -s localhost:8000/api/notifications -H "Authorization: Bearer $CUSTOMER_TOKEN"
# [{"type": "OrderShippedNotification", "message": "Your order #1 has shipped.", …}]
```

## 5 — Review → moderation → live aggregate

Back on the PDP the (verified-purchaser) customer submits a ★5 review — it's **pending** and
invisible publicly. In `/admin/reviews` approve it: the PDP now shows the review and the
denormalized `★★★★★ 5 · 1` aggregate (`s19-review-live.png`). Back-in-stock alerts ride the same
queued-notification rail (see `tests/integration/test_stock_alerts_live.py`).

## 6 — The checkout trace in Grafana/Tempo (OTLP)

With `OTEL_ENABLED=true` (`.env`) every request exports to the LGTM container. Find the checkout:

```bash
curl -s 'localhost:3200/api/search?q=%7B%20name%20%3D~%20%22.*checkout.*%22%20%7D&limit=5' | jq '.traces[].traceID'
```

Open Grafana (`localhost:3000` → Explore → Tempo → TraceQL → paste the ID). The trace shows
`POST /api/checkout` → the `checkout.place_order` business span → its `db SELECT/UPDATE/INSERT`
children, `cache increment`, and the `job SendQueuedMailable` / `job FulfillOrderJob` dispatches —
22 spans (`s19-tempo-checkout-trace.png`).

## 7 — Operability

Maintenance mode (`arvel down`/`up`, health-exempt) and the scheduler are covered in
[operability.md](operability.md).
