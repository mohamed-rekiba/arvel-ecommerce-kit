"""Authorization policy for Product — catalog mutation is gated on the RBAC catalog.* permissions,
not a single admin flag. Anyone may view; create/update/delete require the matching
permission. ``deny_as_not_found`` hides existence on update/delete so a caller without the permission
can't probe which product ids exist. super-admin bypasses every check via the Gate.before hook.
"""

from typing import Any

from arvel.auth.gate import GateResponse

from app.enums import Permission


class ProductPolicy:
    # arvel's resource-ability convention names the index ability "viewAny" (ported
    # literally — Gate._resolve does a plain getattr(policy, ability), no snake_case folding), so the
    # method has to be spelled that exact way to be found; `view_any` silently no-ops to a 403 instead.
    def viewAny(self, user: Any, *_: Any) -> bool:  # noqa: N802 — framework-mandated ability name
        return True

    def view(self, user: Any, *_: Any) -> bool:
        return True

    async def create(self, user: Any, *_: Any) -> GateResponse:
        if user is not None and await user.has_permission_to(
            Permission.CATALOG_CREATE.value
        ):
            return GateResponse.allow()
        return GateResponse.deny("You may not create products.")

    async def update(self, user: Any, *_: Any) -> GateResponse:
        if user is not None and await user.has_permission_to(
            Permission.CATALOG_UPDATE.value
        ):
            return GateResponse.allow()
        return GateResponse.deny_as_not_found()

    async def delete(self, user: Any, *_: Any) -> GateResponse:
        if user is not None and await user.has_permission_to(
            Permission.CATALOG_DELETE.value
        ):
            return GateResponse.allow()
        return GateResponse.deny_as_not_found()
