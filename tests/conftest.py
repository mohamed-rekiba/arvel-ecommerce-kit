"""Shared test fixtures."""

import os

# The suite is infra-independent: force in-process cache/queue regardless of a developer's local
# .env (which may point at Redis for `arvel serve`). Set before any app boots — arvel's
# load_dotenv(override=False) then leaves these alone. The production path uses whatever .env /
# docker-compose provides; tests must not depend on running infra.
os.environ.setdefault("CACHE_STORE", "array")
os.environ.setdefault("QUEUE_CONNECTION", "memory")
os.environ.setdefault("MAIL_MAILER", "log")
os.environ.setdefault("SEARCH_DRIVER", "array")
os.environ.setdefault("FILESYSTEM_DISK", "local")
os.environ.setdefault("PAYMENT_GATEWAY_URL", "https://payments.example.test")
# a non-default secret: webhook verification fails closed on the shipped default outside debug
os.environ.setdefault("PAYMENT_GATEWAY_SECRET", "kit-test-webhook-secret")
os.environ.setdefault("APP_URL", "http://testserver.local")
os.environ.setdefault(
    "APP_KEY", "YXJ2ZWwta2l0LXRlc3Qta2V5LTAxMjM0NTY3ODlhYmM="
)  # a fixed Fernet key for signing/crypto in tests

import pytest

from arvel.http import reset_rate_limiter, reset_sessions


@pytest.fixture(autouse=True)
def _isolate_process_global_state():
    """The api-group rate limiter (and the in-process session store) are process-global, so they
    leak across the per-test app instances a suite builds in one process — without this, the api
    throttle 429s spuriously once the cumulative request count crosses the limit. Reset before each
    test so every test starts from a clean limiter."""
    reset_rate_limiter()
    reset_sessions()
    yield
