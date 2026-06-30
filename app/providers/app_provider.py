"""The application's service provider — register bindings + boot-time wiring."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from arvel.kernel import ServiceProvider

if TYPE_CHECKING:
    from arvel.http import Request

    from app.models.user import User


class AppServiceProvider(ServiceProvider):
    def register(self) -> None:
        """Bind your services into the container."""
        from app.auth.admin_oidc import build_admin_oidc_guard
        from database.seeders.database_seeder import DatabaseSeeder

        def _seeder(_app: Any) -> DatabaseSeeder:
            return DatabaseSeeder()

        # The API guard: resolve the request's user from its bearer token, so
        # AuthenticateMiddleware can populate `current_user` (Laravel Sanctum guard).
        async def _resolve_user(request: Request) -> User | None:
            from arvel.auth.tokens import TokenGuard

            from app.models.user import User

            user_id = await TokenGuard().user_id(request)
            return await User.find(user_id) if user_id is not None else None

        def _user_resolver(_app: Any) -> Any:
            return _resolve_user

        # The admin OIDC guard (validates a Keycloak JWT against the realm JWKS). Lazy so the app
        # boots without Keycloak reachable; a test rebinds it with a fake-verifier guard.
        def _oidc_guard(_app: Any) -> Any:
            return build_admin_oidc_guard()

        self.app.singleton("seeder", _seeder)
        self.app.singleton("user_resolver", _user_resolver)
        self.app.singleton("admin_oidc_guard", _oidc_guard)

    def boot(self) -> None:
        """Boot-time wiring (runs after every provider has registered)."""
        # Register authorization policies on the app-bound Gate (Laravel AuthServiceProvider).
        from app.models.product import Product
        from app.policies.product_policy import ProductPolicy

        if self.app.bound("gate"):
            self.app.make("gate").policy(Product, ProductPolicy())

        # Register event listeners (Laravel EventServiceProvider).
        if self.app.bound("events"):
            from app.listeners.dispatch_fulfillment import dispatch_fulfillment
            from app.listeners.record_order_metrics import record_order_metrics
            from app.listeners.send_order_confirmation import send_order_confirmation

            events = self.app.make("events")
            events.listen("order.placed", record_order_metrics)
            events.listen("order.placed", send_order_confirmation)
            events.listen("order.placed", dispatch_fulfillment)
