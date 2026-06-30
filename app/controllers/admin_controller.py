"""Admin endpoints authenticated via OIDC (Keycloak), distinct from the customer token flow."""

from arvel.http import Request

from app.auth.admin_oidc import resolve_admin
from app.enums import UserRole
from app.schemas import AdminMeOut


async def me(request: Request) -> AdminMeOut:
    """The current admin's identity, resolved from the Keycloak OIDC token (401 without a valid
    token, 403 without the admin realm role)."""
    admin = await resolve_admin(request)
    role = admin.role
    return AdminMeOut(
        id=admin.id,
        name=admin.name,
        email=admin.email,
        role=role.value if isinstance(role, UserRole) else str(role),
    )
