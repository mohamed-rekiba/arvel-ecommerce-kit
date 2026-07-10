"""API routes — the "api" group (served under /api), with a bearer-token auth flow.

Handlers are typed with ``arvel.Schema`` so the OpenAPI request/response schemas generate (browse them
at /schema) AND the request body is validated — a missing or malformed body is a clean 400, not a 500:
  POST /api/login  -> verify credentials, issue a personal access token
  GET  /api/user   -> protected; requires ``Authorization: Bearer <token>``

Guarded subtrees are declared as ``Route.group(...)`` blocks (K3): prefix, name, the
``Authenticate`` middleware, and the ``bearer`` OpenAPI security scheme are stated once per
subtree instead of repeated on every route (DR-0052 lets a group carry ``secure=`` alongside
``middleware=``, so enforcement and its documentation can't drift apart).
"""

from arvel import Route, Schema, abort, config
from arvel.auth.middleware import Authenticate, Authorize
from arvel.auth.tokens import TokenGuard, create_token
from arvel.http import Request
from arvel.security import Hasher

from app.controllers import account_controller as account
from app.controllers import admin_controller as admin
from app.controllers import admin_coupon_controller as admin_coupons
from app.controllers import admin_deal_controller as admin_deals
from app.controllers import address_controller as addresses
from app.controllers import announcement_controller as announcement
from app.controllers import banner_controller as banners
from app.controllers import admin_media_controller as media_library
from app.controllers import invoice_controller as invoice
from app.controllers import settings_controller as settings
from app.controllers import deal_controller as deals
from app.controllers import admin_product_controller as admin_products
from app.controllers import admin_rbac_controller as rbac
from app.controllers import admin_taxonomy_controller as taxonomy
from app.controllers import admin_user_controller as admin_users
from app.controllers import admin_variant_controller as admin_variants
from app.controllers import auth_controller as auth
from app.controllers import cart_controller as cart
from app.controllers import catalog_controller as catalog
from app.controllers import review_controller as reviews
from app.controllers import stock_alert_controller as stock_alerts
from app.controllers import checkout_controller as checkout
from app.controllers import media_controller as media
from app.controllers import notification_controller as notifications
from app.controllers import wishlist_controller as wishlist
from app.controllers import payment_controller as payment
from app.enums import Permission
from app.models.user import User
from app.schemas import CredentialsIn, TokenOut, UserOut


class HealthStatus(Schema):
    status: str


async def health(request: Request) -> HealthStatus:
    """Liveness probe."""
    return HealthStatus(status="ok")


async def login(request: Request, data: CredentialsIn) -> TokenOut:
    """Verify credentials and issue a personal access token (merging any guest cart the request
    carries — build-a-cart-then-sign-in must never strand items)."""
    user = await User.where("email", data.email).first()
    if user is None or not Hasher().check(data.password, user.password):
        abort(401, "Invalid credentials")
    await cart.merge_guest_cart(request, user)
    from app.i18n import active_locale

    locale = active_locale()
    if getattr(user, "locale", None) != locale:
        user.locale = (
            locale  # the sign-in language becomes the mail/notification language
        )
        await user.save()
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
    from app.controllers.account_controller import user_out

    return await user_out(user)


Route.get("/health", health, name="api.health")
Route.post("/login", login, name="api.login").status(
    200
)  # action, not a resource creation
# secure-only: no Authenticate — a bearer token is optional context, not a requirement, here
Route.get("/user", me, name="api.user").secure("bearer")

# --- Customer auth ---
Route.post("/register", auth.register, name="api.register")  # creates a user → 201
Route.post("/logout", auth.logout, name="api.logout").status(200).secure("bearer")
Route.post("/forgot-password", auth.forgot_password, name="api.password.forgot").status(
    200
)
Route.post("/reset-password", auth.reset_password, name="api.password.reset").status(
    200
)
# the link target is public — the signed token IS the credential
Route.post("/email/verify", account.verify_email, name="api.email.verify").status(200)

# --- Catalog (public read API) ---
Route.get("/categories", catalog.categories_index, name="api.categories.index")
Route.get("/products", catalog.products_index, name="api.products.index")
Route.get("/products/feed", catalog.products_feed, name="api.products.feed")
Route.get("/products/{slug:str}", catalog.products_show, name="api.products.show")
# Media library: serve a gallery item (original) or a named conversion (thumb/preview)
Route.get("/media/{id:int}", media.serve_media, name="api.media.show")
Route.get(
    "/media/{id:int}/{conversion:str}", media.serve_media, name="api.media.conversion"
)

# --- Product reviews (verified purchasers; moderated) ---
Route.get(
    "/products/{slug:str}/reviews", reviews.index, name="api.products.reviews.index"
)

# --- Cart (guest by X-Cart-Token, or the authenticated user's cart) ---
Route.get("/cart", cart.show, name="api.cart.show")
Route.post("/cart/items", cart.add_item, name="api.cart.items.add")
Route.patch("/cart/items/{id:int}", cart.update_item, name="api.cart.items.update")
Route.delete("/cart/items/{id:int}", cart.remove_item, name="api.cart.items.remove")

# --- Cart coupon (guest or signed-in) ---
Route.post("/cart/coupon", cart.apply_coupon, name="api.cart.coupon.apply").status(200)
Route.delete("/cart/coupon", cart.remove_coupon, name="api.cart.coupon.remove").status(
    200
)

# --- Deals (flash sales) ---
Route.get("/deals", deals.index, name="api.deals.index")
Route.get("/announcement", announcement.show, name="api.announcement")

# --- Settings + newsletter ---
Route.get("/settings", settings.public_settings, name="api.settings")
Route.post("/newsletter", settings.subscribe, name="api.newsletter").status(200)

# --- Hero banners ---
Route.get("/banners", banners.index, name="api.banners.index")

# --- Checkout & orders ---
Route.post("/checkout", checkout.checkout, name="api.checkout")
Route.get(
    "/metrics/orders-placed",
    checkout.orders_placed_count,
    name="api.metrics.orders_placed",
)
# One order: the signed-in owner (bearer) OR the holder of the order's access token
# (X-Order-Token, issued at checkout) — controller-level ownership, so guests can use it.
Route.get("/orders/{id:int}", checkout.show, name="api.orders.show")
Route.get("/orders/{id:int}/invoice", invoice.show, name="api.orders.invoice")
Route.post("/orders/{id:int}/cancel", checkout.cancel, name="api.orders.cancel").status(
    200
)  # a transition, not a creation

# --- Payments ---
# Pay: signed-in owner OR guest order-token holder (guests must be able to pay) — the ownership
# check lives in the controller (resolve_owned_order), not a bearer-only middleware.
Route.post("/orders/{id:int}/pay", payment.pay, name="api.orders.pay")
Route.post(
    "/webhooks/payment", payment.webhook, name="api.webhooks.payment"
)  # gateway → us

# --- Bare guarded: no shared prefix, so grouped for middleware+security only ---
with Route.group(middleware=[Authenticate], secure=["bearer"]):
    Route.patch("/user", account.update_profile, name="api.user.update")
    Route.put(
        "/user/password", account.change_password, name="api.user.password"
    ).status(200)
    Route.post(
        "/email/verification-notification",
        account.send_verification,
        name="api.email.verification.send",
    ).status(200)
    # topical sibling (GET /products/{slug}/reviews) is public; this one-off needs its own auth
    Route.post(
        "/products/{slug:str}/reviews", reviews.store, name="api.products.reviews.store"
    )
    # topical siblings (GET /orders/{id}, /orders/{id}/invoice) are public; this one needs auth
    Route.get("/orders", checkout.my_orders, name="api.orders.index")

# --- Account self-service (avatar + address book) ---
with Route.group(
    prefix="/account", name="api.account.", middleware=[Authenticate], secure=["bearer"]
):
    Route.post("/avatar", account.upload_avatar, name="avatar")
    Route.get("/addresses", addresses.index, name="addresses.index")
    Route.post("/addresses", addresses.store, name="addresses.store")
    Route.patch("/addresses/{id:int}", addresses.update, name="addresses.update")
    Route.delete("/addresses/{id:int}", addresses.destroy, name="addresses.destroy")

# --- Customer notifications (database channel of the notification system) ---
with Route.group(
    prefix="/notifications",
    name="api.notifications.",
    middleware=[Authenticate],
    secure=["bearer"],
):
    Route.get("", notifications.index, name="index")
    Route.post("/read", notifications.mark_read, name="read").status(200)

# --- Customer wishlist (saved products) ---
with Route.group(
    prefix="/wishlist",
    name="api.wishlist.",
    middleware=[Authenticate],
    secure=["bearer"],
):
    Route.get("", wishlist.index, name="index")
    Route.post("/{product_id:int}", wishlist.toggle, name="toggle").status(200)

# --- Back-in-stock alerts (signed-in customers) ---
with Route.group(
    prefix="/variants/{id:int}/stock-alert",
    name="api.variants.stock_alert.",
    middleware=[Authenticate],
    secure=["bearer"],
):
    Route.post("", stock_alerts.subscribe, name="subscribe").status(200)
    Route.delete("", stock_alerts.unsubscribe, name="unsubscribe").status(200)

# --- Admin (nested: OIDC self-service outer, bearer-guarded operations inner) ---
with Route.group(prefix="/admin", name="api.admin."):
    Route.get("/me", admin.me, name="me").secure("oidc")
    # Exchange a Keycloak token (from the SPA's auth-code+PKCE flow) for an arvel bearer PAT.
    Route.post("/oidc/token", admin.oidc_exchange, name="oidc.token").status(
        200
    ).secure("oidc")

    with Route.group(middleware=[Authenticate], secure=["bearer"]):
        # Admin product CRUD (auth-guarded by middleware; policy-guarded in the controller).
        # Authenticate (401 if guest) runs as route middleware BEFORE body parsing, so an
        # unauthenticated request never reaches parsing/policy checks; the ProductPolicy then
        # decides admin-vs-customer (403/404) inside the controller. Admin listings return
        # EVERY row (incl. hidden) with an is_visible flag — vs the storefront, which only
        # returns the retrievable set.
        # catalog.update as route middleware (DR-0055): it runs in the pipeline before route-model
        # binding resolves, so a denied caller gets a uniform 403 whether or not the product id
        # exists — binding alone would otherwise 404 a nonexistent id before the handler's own
        # check ever ran, leaking existence to any authenticated non-admin.
        Route.post(
            "/products/{id:int}/image", media.upload_image, name="products.image"
        ).middleware(Authorize(Permission.CATALOG_UPDATE.value))
        Route.delete(
            "/products/{id:int}/media/{media_id:int}",
            media.delete_image,
            name="products.media.destroy",
        ).status(200).middleware(Authorize(Permission.CATALOG_UPDATE.value))
        Route.get("/products", admin_products.products_index, name="products.index")
        Route.get(
            "/categories", admin_products.categories_index, name="categories.index"
        )
        Route.get("/products/{id:int}", admin_products.show, name="products.show")
        Route.post("/products", admin_products.store, name="products.store")
        Route.put("/products/{id:int}", admin_products.update, name="products.update")
        Route.delete(
            "/products/{id:int}", admin_products.destroy, name="products.destroy"
        )
        Route.post(
            "/products/{id:int}/restore",
            admin_products.restore,
            name="products.restore",
        ).status(200)

        # Admin categories + vendors (the retrievability dimensions; catalog.* authority).
        # update/destroy carry Authorize (DR-0055) — see the products.image comment above for why.
        Route.post("/categories", taxonomy.category_store, name="categories.store")
        Route.put(
            "/categories/{id:int}", taxonomy.category_update, name="categories.update"
        ).middleware(Authorize(Permission.CATALOG_UPDATE.value))
        Route.delete(
            "/categories/{id:int}", taxonomy.category_destroy, name="categories.destroy"
        ).status(200).middleware(Authorize(Permission.CATALOG_DELETE.value))
        Route.get("/vendors", taxonomy.vendors_index, name="vendors.index")
        Route.post("/vendors", taxonomy.vendor_store, name="vendors.store")
        Route.put(
            "/vendors/{id:int}", taxonomy.vendor_update, name="vendors.update"
        ).middleware(Authorize(Permission.CATALOG_UPDATE.value))

        # Admin variants + stock (nested under the product; catalog.update authority).
        Route.get(
            "/products/{id:int}/variants", admin_variants.index, name="variants.index"
        )
        Route.post(
            "/products/{id:int}/variants", admin_variants.store, name="variants.store"
        )
        # nested under the product so a variant id belonging to a DIFFERENT product 404s via the
        # scoped binding itself (E6), not a controller re-check.
        Route.patch(
            "/products/{id:int}/variants/{variant_id:int}",
            admin_variants.update,
            name="variants.update",
        ).scope_bindings()
        Route.post(
            "/products/{id:int}/variants/{variant_id:int}/stock",
            admin_variants.adjust_stock,
            name="variants.stock",
        ).status(200).scope_bindings()
        Route.delete(
            "/products/{id:int}/variants/{variant_id:int}",
            admin_variants.destroy,
            name="variants.destroy",
        ).status(200).scope_bindings()

        # Admin user directory (users.view; role mutations stay on roles.manage). Authorize
        # (DR-0055) on the id-bound routes — see the products.image comment above for why.
        Route.get("/users", admin_users.index, name="users.index")
        Route.get("/users/{id:int}", admin_users.show, name="users.show").middleware(
            Authorize(Permission.USERS_VIEW.value)
        )

        # Admin RBAC + audit (roles.manage / audit.view; super-admin bypasses).
        Route.get("/roles", rbac.roles_index, name="roles.index")
        Route.get("/permissions", rbac.permissions_index, name="permissions.index")
        Route.get(
            "/users/{id:int}/roles", rbac.user_roles, name="users.roles"
        ).middleware(Authorize(Permission.ROLES_MANAGE.value))
        Route.post(
            "/users/{id:int}/roles", rbac.assign_role, name="users.roles.assign"
        ).status(200).middleware(Authorize(Permission.ROLES_MANAGE.value))
        Route.delete(
            "/users/{id:int}/roles/{role:str}",
            rbac.revoke_role,
            name="users.roles.revoke",
        ).status(200).middleware(Authorize(Permission.ROLES_MANAGE.value))
        Route.get("/audit", rbac.audit_index, name="audit.index")

        # Admin reviews. moderate carries Authorize (DR-0055).
        Route.get("/reviews", reviews.admin_index, name="reviews.index")
        Route.post(
            "/reviews/{id:int}/{decision:str}",
            reviews.moderate,
            name="reviews.moderate",
        ).status(200).middleware(Authorize(Permission.REVIEWS_MODERATE.value))

        # Admin settings + media + newsletter.
        Route.get("/settings", settings.admin_settings, name="settings")
        Route.patch("/settings", settings.update_settings, name="settings.update")
        Route.get("/media", media_library.index, name="media")
        Route.get("/newsletter", settings.newsletter_index, name="newsletter")

        # Admin banners. Every action here carries Authorize (DR-0055) — reviewed as a whole
        # resource, not just the id-bound ones, so the surface has one consistent authz posture.
        Route.get("/banners", banners.admin_index, name="banners.index").middleware(
            Authorize(Permission.CATALOG_VIEW.value)
        )
        Route.post("/banners", banners.store, name="banners.store").middleware(
            Authorize(Permission.CATALOG_CREATE.value)
        )
        Route.patch(
            "/banners/{id:int}", banners.update, name="banners.update"
        ).middleware(Authorize(Permission.CATALOG_UPDATE.value))
        Route.delete(
            "/banners/{id:int}", banners.destroy, name="banners.destroy"
        ).middleware(Authorize(Permission.CATALOG_DELETE.value))
        Route.post(
            "/banners/{id:int}/image", banners.upload_image, name="banners.image"
        ).middleware(Authorize(Permission.CATALOG_UPDATE.value))

        # Admin deals. update/destroy carry Authorize (DR-0055).
        Route.get("/deals", admin_deals.index, name="deals.index")
        Route.post("/deals", admin_deals.store, name="deals.store")
        Route.patch(
            "/deals/{id:int}", admin_deals.update, name="deals.update"
        ).middleware(Authorize(Permission.CATALOG_UPDATE.value))
        Route.delete(
            "/deals/{id:int}", admin_deals.destroy, name="deals.destroy"
        ).middleware(Authorize(Permission.CATALOG_DELETE.value))

        # Admin coupons (catalog authority). update carries Authorize (DR-0055).
        Route.get("/coupons", admin_coupons.index, name="coupons.index")
        Route.post("/coupons", admin_coupons.store, name="coupons.store")
        Route.patch(
            "/coupons/{id:int}", admin_coupons.update, name="coupons.update"
        ).middleware(Authorize(Permission.CATALOG_UPDATE.value))

        # Admin orders. show/status carry Authorize (DR-0055) — see the products.image comment
        # above for why a class-level admin check has to move ahead of route-model binding.
        Route.get("/orders", checkout.admin_orders_index, name="orders.index")
        Route.get(
            "/orders/{id:int}", checkout.admin_order_show, name="orders.show"
        ).middleware(Authorize(Permission.ORDERS_VIEW.value))
        Route.post(
            "/orders/{id:int}/status", checkout.update_status, name="orders.status"
        ).status(200).middleware(
            Authorize(Permission.ORDERS_UPDATE.value)
        )  # a transition, not a creation

# --- Dev payment gateway (debug builds only) ---
# A stand-in PSP so the payment loop runs live with no external account: charges succeed and the
# signed webhook arrives asynchronously via the queue. Never registered when app.debug is off.
if config("app.debug", False):
    from app.controllers import dev_gateway_controller as dev_gateway

    Route.post(
        "/dev-gateway/charges",
        dev_gateway.create_charge,
        name="api.dev_gateway.charges",
    )
