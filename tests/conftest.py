"""Shared test fixtures."""

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
