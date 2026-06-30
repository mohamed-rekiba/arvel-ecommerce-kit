"""Global HTTP middleware (cf. Laravel's withMiddleware).

List middleware classes/instances here; they run for every request, in order. Add your own — or
arvel's built-ins — to the list.
"""

from arvel.http.middleware import AuthenticateMiddleware

# AuthenticateMiddleware resolves the request's user via the `user_resolver` binding (see
# AppServiceProvider) and binds it to `current_user` for the request — so the Gate and the
# `Authenticate`/`Authorize` route middleware see the authenticated user. It never rejects on its
# own (public routes stay public); route-level `Authenticate` enforces the 401.
middlewares: list = [AuthenticateMiddleware]
