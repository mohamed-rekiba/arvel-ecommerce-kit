"""Authorization policy for Product — only admins may mutate the catalog (Laravel Policy parity).

The ability name maps to the method name exactly (arvel does no snake/camel conversion). Anyone may
view; create/update/delete require an admin. ``deny_as_not_found`` hides existence on update/delete
so a non-admin can't probe which product ids exist.
"""

from typing import Any

from arvel.auth.gate import GateResponse


class ProductPolicy:
    def view_any(self, user: Any, *_: Any) -> bool:
        return True

    def view(self, user: Any, *_: Any) -> bool:
        return True

    def create(self, user: Any, *_: Any) -> GateResponse:
        if user is not None and user.is_admin():
            return GateResponse.allow()
        return GateResponse.deny("Only admins may create products.")

    def update(self, user: Any, *_: Any) -> GateResponse:
        if user is not None and user.is_admin():
            return GateResponse.allow()
        return GateResponse.deny_as_not_found()

    def delete(self, user: Any, *_: Any) -> GateResponse:
        if user is not None and user.is_admin():
            return GateResponse.allow()
        return GateResponse.deny_as_not_found()
