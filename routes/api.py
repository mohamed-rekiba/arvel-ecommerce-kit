"""API routes — the "api" group (served under /api), with a bearer-token auth flow.

Handlers are typed with ``arvel.Schema`` so the OpenAPI request/response schemas generate (browse them
at /schema) AND the request body is validated — a missing or malformed body is a clean 400, not a 500:
  POST /api/login  -> verify credentials, issue a personal access token
  GET  /api/user   -> protected; requires ``Authorization: Bearer <token>``
"""

from arvel import Route, Schema, abort
from arvel.auth.middleware import Authenticate
from arvel.auth.tokens import TokenGuard, create_token
from arvel.http import Request
from arvel.security import Hasher

from app.controllers import admin_controller as admin
from app.controllers import admin_product_controller as admin_products
from app.controllers import admin_rbac_controller as rbac
from app.controllers import auth_controller as auth
from app.controllers import cart_controller as cart
from app.controllers import catalog_controller as catalog
from app.controllers import checkout_controller as checkout
from app.controllers import media_controller as media
from app.controllers import payment_controller as payment
from app.models.user import User
from app.schemas import CredentialsIn, TokenOut, UserOut


class HealthStatus(Schema):
    status: str


async def health(request: Request) -> HealthStatus:
    """Liveness probe."""
    return HealthStatus(status="ok")


async def login(request: Request, data: CredentialsIn) -> TokenOut:
    """Verify credentials and issue a personal access token."""
    user = await User.where("email", data.email).first()
    if user is None or not Hasher().check(data.password, user.password):
        abort(401, "Invalid credentials")
    token, _ = await create_token(user, name="api")
    return TokenOut(token=token)


async def me(request: Request) -> UserOut:
    """The authenticated user (requires a bearer token)."""
    user_id = await TokenGuard().user_id(request)
    if user_id is None:
        abort(401, "Unauthenticated")
    user = await User.find(user_id)
    if user is None:
        abort(401, "Unauthenticated")
    return UserOut(id=user.id, name=user.name, email=user.email)


Route.get("/health", health, name="api.health")
Route.post("/login", login, name="api.login").status(
    200
)  # action, not a resource creation
Route.get("/user", me, name="api.user").secure(
    "bearer"
)  # shows the lock + 'Authorize' in API docs

# --- Customer auth ------------------------------------------------------------
Route.post("/register", auth.register, name="api.register")  # creates a user → 201
Route.post("/logout", auth.logout, name="api.logout").status(200).secure("bearer")
Route.post("/forgot-password", auth.forgot_password, name="api.password.forgot").status(
    200
)
Route.post("/reset-password", auth.reset_password, name="api.password.reset").status(
    200
)

# --- Catalog (public read API) ------------------------------------------------
Route.get("/categories", catalog.categories_index, name="api.categories.index")
Route.get("/products", catalog.products_index, name="api.products.index")
Route.get("/products/{slug:str}", catalog.products_show, name="api.products.show")
# Media library: serve a gallery item (original) or a named conversion (thumb/preview)
Route.get("/media/{id:int}", media.serve_media, name="api.media.show")
Route.get(
    "/media/{id:int}/{conversion:str}", media.serve_media, name="api.media.conversion"
)
Route.post(
    "/admin/products/{id:int}/image",
    media.upload_image,
    name="api.admin.products.image",
).middleware(Authenticate).secure("bearer")

# --- Admin product CRUD (auth-guarded by middleware; policy-guarded in the controller) --------
# Authenticate (401 if guest) runs as route middleware BEFORE body parsing — Laravel ordering; the
# ProductPolicy then decides admin-vs-customer (403/404) inside the controller.
# Admin listings return EVERY row (incl. hidden) with an is_visible flag — vs the storefront, which
# only returns the retrievable set.
Route.get(
    "/admin/products", admin_products.products_index, name="api.admin.products.index"
).middleware(Authenticate).secure("bearer")
Route.get(
    "/admin/categories",
    admin_products.categories_index,
    name="api.admin.categories.index",
).middleware(Authenticate).secure("bearer")
Route.post(
    "/admin/products", admin_products.store, name="api.admin.products.store"
).middleware(Authenticate).secure("bearer")
Route.put(
    "/admin/products/{id:int}", admin_products.update, name="api.admin.products.update"
).middleware(Authenticate).secure("bearer")
Route.delete(
    "/admin/products/{id:int}",
    admin_products.destroy,
    name="api.admin.products.destroy",
).middleware(Authenticate).secure("bearer")

# --- Admin RBAC + audit (roles.manage / audit.view; super-admin bypasses) -----
Route.get("/admin/roles", rbac.roles_index, name="api.admin.roles.index").middleware(
    Authenticate
).secure("bearer")
Route.get(
    "/admin/permissions", rbac.permissions_index, name="api.admin.permissions.index"
).middleware(Authenticate).secure("bearer")
Route.get(
    "/admin/users/{id:int}/roles", rbac.user_roles, name="api.admin.users.roles"
).middleware(Authenticate).secure("bearer")
Route.post(
    "/admin/users/{id:int}/roles", rbac.assign_role, name="api.admin.users.roles.assign"
).status(200).middleware(Authenticate).secure("bearer")
Route.delete(
    "/admin/users/{id:int}/roles/{role:str}",
    rbac.revoke_role,
    name="api.admin.users.roles.revoke",
).status(200).middleware(Authenticate).secure("bearer")
Route.get("/admin/audit", rbac.audit_index, name="api.admin.audit.index").middleware(
    Authenticate
).secure("bearer")

# --- Admin (OIDC / Keycloak) --------------------------------------------------
Route.get("/admin/me", admin.me, name="api.admin.me").secure("oidc")
# Exchange a Keycloak token (from the SPA's auth-code+PKCE flow) for an arvel bearer PAT (DR-0030).
Route.post("/admin/oidc/token", admin.oidc_exchange, name="api.admin.oidc.token").status(200).secure("oidc")

# --- Cart (guest by X-Cart-Token, or the authenticated user's cart) -----------
Route.get("/cart", cart.show, name="api.cart.show")
Route.post("/cart/items", cart.add_item, name="api.cart.items.add")
Route.patch("/cart/items/{id:int}", cart.update_item, name="api.cart.items.update")
Route.delete("/cart/items/{id:int}", cart.remove_item, name="api.cart.items.remove")

# --- Checkout & orders --------------------------------------------------------
Route.post("/checkout", checkout.checkout, name="api.checkout")
Route.get(
    "/metrics/orders-placed",
    checkout.orders_placed_count,
    name="api.metrics.orders_placed",
)
Route.get("/orders", checkout.my_orders, name="api.orders.index").middleware(
    Authenticate
).secure("bearer")
Route.get("/admin/orders", checkout.admin_orders_index, name="api.admin.orders.index").middleware(
    Authenticate
).secure("bearer")
Route.post(
    "/admin/orders/{id:int}/status",
    checkout.update_status,
    name="api.admin.orders.status",
).status(200).middleware(Authenticate).secure("bearer")  # a transition, not a creation

# --- Payments -----------------------------------------------------------------
Route.post("/orders/{id:int}/pay", payment.pay, name="api.orders.pay").middleware(
    Authenticate
).secure("bearer")
Route.post(
    "/webhooks/payment", payment.webhook, name="api.webhooks.payment"
)  # gateway → us
