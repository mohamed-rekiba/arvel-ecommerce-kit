"""Third-party service credentials / endpoints (cf. Laravel config/services.php)."""

from arvel import env

config = {
    "payment_gateway": {
        # the mock gateway in tests intercepts via a MockTransport; in prod point this at the real API
        "url": env("PAYMENT_GATEWAY_URL", "https://payments.example.test"),
        "secret": env("PAYMENT_GATEWAY_SECRET", "test-secret"),
    },
}
