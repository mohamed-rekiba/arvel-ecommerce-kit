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
        from app.console.search_reindex import SearchReindexCommand
        from database.seeders.database_seeder import DatabaseSeeder

        # A Command class (not a routes/console.py closure) — see search_reindex.py for why.
        self.commands(SearchReindexCommand)

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
        # K14 — "promoted-deals": the storefront's Deals-of-the-Day rail ordered by best-discount
        # first for an English-locale shopper (an i18n-gated rollout), soonest-ending-first
        # otherwise. A guest (scope None) resolves to the control.
        from arvel.features import Feature

        def _promoted_deals_segment(user: Any) -> bool:
            return getattr(user, "mail_locale", None) == "en"

        Feature.define("promoted-deals", _promoted_deals_segment)

        # Product's policy is declared on the model (__policy__ — the Gate's preferred,
        # typed form); only the Gate-wide hooks and ability defines are wired here.
        if self.app.bound("gate"):
            gate = self.app.make("gate")

            # super-admin bypasses every ability (a gate before-hook → auto-grant).
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

        # Register event listeners.
        if self.app.bound("events"):
            from arvel.auth.password_reset import PasswordResetRequested

            from app.listeners.dispatch_fulfillment import dispatch_fulfillment
            from app.listeners.record_order_metrics import record_order_metrics
            from app.listeners.send_order_confirmation import send_order_confirmation
            from app.listeners.send_password_reset import send_password_reset

            events = self.app.make("events")
            events.listen("order.placed", record_order_metrics)
            events.listen("order.placed", send_order_confirmation)
            events.listen("order.placed", dispatch_fulfillment)
            events.listen(PasswordResetRequested, send_password_reset)

        # K9 — the order's private broadcast channel authorizes only its owner; a non-owner (or a
        # guest) gets a deny, which arvel's /broadcasting/auth turns into a 403.
        if self.app.bound("broadcast"):
            from app.models.order import Order

            async def _order_owner(user: Any, order_id: str) -> bool:
                if user is None:
                    return False
                order = await Order.find(int(order_id))
                return order is not None and order.user_id == user.id

            self.app.make("broadcast").channel("order.{id}", _order_owner)
