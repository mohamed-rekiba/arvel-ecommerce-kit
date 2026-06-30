"""Admin endpoints authenticated via OIDC (Keycloak), distinct from the customer token flow."""

from typing import Any

from app.auth.admin_oidc import resolve_admin


async def me(request) -> Any:
    """GET /api/admin/me — the current admin's identity, resolved from the Keycloak OIDC token
    (401 without a valid token, 403 without the admin realm role)."""
    admin = await resolve_admin(request)
    return {"id": admin.id, "name": admin.name, "email": admin.email, "role": admin.role.value}
