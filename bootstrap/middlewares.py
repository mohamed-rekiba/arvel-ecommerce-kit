"""Global HTTP middleware (cf. Laravel's withMiddleware).

List middleware classes/instances here; they run for every request, in order. Add your own — or
arvel's built-ins — to the list.
"""

from typing import Any

from arvel.http.middleware import AuthenticateMiddleware

# Resolves the request's user via the `user_resolver` binding and populates `current_user` so the
# Gate and route middleware see it. Never rejects on its own — route-level `Authenticate` enforces
# the 401.
middlewares: list[Any] = [AuthenticateMiddleware]
