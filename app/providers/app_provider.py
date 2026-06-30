"""The application's service provider — register bindings + boot-time wiring."""

from arvel.kernel import ServiceProvider


class AppServiceProvider(ServiceProvider):
    def register(self) -> None:
        """Bind your services into the container."""
        # Make `arvel db:seed` run the root seeder.
        from database.seeders.database_seeder import DatabaseSeeder

        self.app.singleton("seeder", lambda _app: DatabaseSeeder())

        # Bind the API guard: resolve the request's user from its bearer token, so
        # AuthenticateMiddleware can populate `current_user` (Laravel Sanctum guard).
        async def _resolve_user(request):
            from arvel.auth.tokens import TokenGuard

            from app.models.user import User

            user_id = await TokenGuard().user_id(request)
            return await User.find(user_id) if user_id is not None else None

        self.app.singleton("user_resolver", lambda _app: _resolve_user)

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
