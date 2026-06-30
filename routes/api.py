"""API routes — the "api" group (served under /api), with a bearer-token auth flow.

Handlers are typed with ``arvel.Schema`` so the OpenAPI request/response schemas generate (browse them
at /schema) AND the request body is validated — a missing or malformed body is a clean 400, not a 500:
  POST /api/login  -> verify credentials, issue a personal access token
  GET  /api/user   -> protected; requires ``Authorization: Bearer <token>``
"""

from arvel import Route, Schema, abort
from arvel.auth.middleware import Authenticate
from arvel.auth.tokens import TokenGuard, create_token
from arvel.http import Response
from arvel.security import Hasher

from app.controllers import admin_product_controller as admin_products
from app.controllers import auth_controller as auth
from app.controllers import cart_controller as cart
from app.controllers import catalog_controller as catalog
from app.controllers import checkout_controller as checkout
from app.controllers import payment_controller as payment
from app.models.user import User


class HealthStatus(Schema):
    status: str


class Credentials(Schema):
    email: str
    password: str


class UserOut(Schema):
    id: int
    name: str
    email: str


async def health(request) -> HealthStatus:
    return HealthStatus(status="ok")


async def login(request, data: Credentials):  # `data: Credentials` → parsed + validated request body
    user = await User.query().where("email", data.email).first()
    if user is None or not Hasher().check(data.password, user.password):
        abort(401, "Invalid credentials")
    token, _ = await create_token(user, name="api")
    return Response(content={"token": token}, status=200)


async def me(request) -> UserOut:
    user_id = await TokenGuard().user_id(request)
    if user_id is None:
        abort(401, "Unauthenticated")
    user = await User.find(user_id)
    return UserOut(id=user.id, name=user.name, email=user.email)


Route.get("/health", health, name="api.health")
Route.post("/login", login, name="api.login")
Route.get("/user", me, name="api.user").secure("bearer")  # shows the lock + 'Authorize' in API docs

# --- Customer auth ------------------------------------------------------------
Route.post("/register", auth.register, name="api.register")
Route.post("/logout", auth.logout, name="api.logout").secure("bearer")
Route.post("/forgot-password", auth.forgot_password, name="api.password.forgot")
Route.post("/reset-password", auth.reset_password, name="api.password.reset")

# --- Catalog (public read API) ------------------------------------------------
Route.get("/categories", catalog.categories_index, name="api.categories.index")
Route.get("/products", catalog.products_index, name="api.products.index")
Route.get("/products/{slug:str}", catalog.products_show, name="api.products.show")

# --- Admin product CRUD (auth-guarded by middleware; policy-guarded in the controller) --------
# Authenticate (401 if guest) runs as route middleware BEFORE body parsing — Laravel ordering; the
# ProductPolicy then decides admin-vs-customer (403/404) inside the controller.
Route.post("/admin/products", admin_products.store, name="api.admin.products.store").middleware(
    Authenticate
).secure("bearer")
Route.put(
    "/admin/products/{id:int}", admin_products.update, name="api.admin.products.update"
).middleware(Authenticate).secure("bearer")
Route.delete(
    "/admin/products/{id:int}", admin_products.destroy, name="api.admin.products.destroy"
).middleware(Authenticate).secure("bearer")

# --- Cart (guest by X-Cart-Token, or the authenticated user's cart) -----------
Route.get("/cart", cart.show, name="api.cart.show")
Route.post("/cart/items", cart.add_item, name="api.cart.items.add")
Route.patch("/cart/items/{id:int}", cart.update_item, name="api.cart.items.update")
Route.delete("/cart/items/{id:int}", cart.remove_item, name="api.cart.items.remove")

# --- Checkout & orders --------------------------------------------------------
Route.post("/checkout", checkout.checkout, name="api.checkout")
Route.get("/metrics/orders-placed", checkout.orders_placed_count, name="api.metrics.orders_placed")
Route.get("/orders", checkout.my_orders, name="api.orders.index").middleware(Authenticate).secure(
    "bearer"
)
Route.post(
    "/admin/orders/{id:int}/status", checkout.update_status, name="api.admin.orders.status"
).middleware(Authenticate).secure("bearer")

# --- Payments -----------------------------------------------------------------
Route.post("/orders/{id:int}/pay", payment.pay, name="api.orders.pay").middleware(
    Authenticate
).secure("bearer")
Route.post("/webhooks/payment", payment.webhook, name="api.webhooks.payment")  # gateway → us
