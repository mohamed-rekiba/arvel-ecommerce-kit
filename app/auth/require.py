"""Require the authenticated user or 401 — one place, not a copy per controller.

The route's Authenticate middleware already guarantees a user on protected routes; this narrows
current_user's User | None to User (and 401s defensively) so handlers get a typed user.
"""

from arvel import abort
from arvel.support import current_user

from app.i18n import trans
from app.models.user import User


def require_user() -> User:
    user: User | None = current_user.get()
    if user is None:
        abort(401, trans("shop.errors.unauthenticated"))
    return user
