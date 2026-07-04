"""The application's service provider — register bindings + boot-time wiring."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from arvel.kernel import ServiceProvider

if TYPE_CHECKING:
    from arvel.http import Request

    from app.models.user import User


class AppServiceProvider(ServiceProvider):
    def register(self) -> None:
        from app.auth.admin_oidc import build_admin_oidc_guard
        from database.seeders.database_seeder import DatabaseSeeder

        def _seeder(_app: Any) -> DatabaseSeeder:
            return DatabaseSeeder()

        # Resolves the request's user from its bearer token so AuthenticateMiddleware can
        # populate `current_user`.
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
            gate = self.app.make("gate")
            gate.policy(Product, ProductPolicy())

            # super-admin bypasses every ability (Laravel Gate::before → super-admin auto-grant).
            from app.enums import Permission, RoleName

            async def _super_admin_first(user: Any, _ability: str) -> bool | None:
                if user is not None and await user.has_role(RoleName.SUPER_ADMIN.value):
                    return True
                return None

            gate.before(_super_admin_first)

            # Standalone (non-model) abilities → the matching RBAC permission, for every
            # permission (gate.define and the ProductPolicy coexist: the policy still governs
            # Product-model checks).
            def _define(permission: Permission) -> None:
                async def _check(user: Any, *_: Any) -> bool:
                    return user is not None and await user.has_permission_to(
                        permission.value
                    )

                gate.define(permission.value, _check)

            for permission in Permission:
                _define(permission)

        # Catalog visibility: a publish change on a product/category/vendor flags the views dirty;
        # the scheduled refresh_if_dirty (routes/console.py) debounces + recomputes (Laravel observers).
        from app.models.category import Category
        from app.models.vendor import Vendor
        from app.observers.publish_observer import PublishObserver

        observer = PublishObserver()
        for model in (Product, Category, Vendor):
            model.observe(observer)

        # Register event listeners (Laravel EventServiceProvider).
        if self.app.bound("events"):
            from app.listeners.dispatch_fulfillment import dispatch_fulfillment
            from app.listeners.record_order_metrics import record_order_metrics
            from app.listeners.send_order_confirmation import send_order_confirmation

            events = self.app.make("events")
            events.listen("order.placed", record_order_metrics)
            events.listen("order.placed", send_order_confirmation)
            events.listen("order.placed", dispatch_fulfillment)
