"""Admin endpoints authenticated via OIDC (Keycloak), distinct from the customer token flow."""

from arvel.auth.tokens import create_token
from arvel.http import Request

from app.auth.admin_oidc import resolve_admin
from app.enums import UserRole
from app.schemas import AdminMeOut, TokenOut


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


async def oidc_exchange(request: Request) -> TokenOut:
    """Exchange a validated Keycloak token for an arvel bearer PAT (DR-0030). Validates + JIT-provisions
    the admin (resolve_admin), then **persists** the Keycloak-mapped RBAC roles so the issued bearer
    carries them into the bearer-guarded admin APIs. The browser admin SPA calls this after its
    auth-code+PKCE flow, then uses the returned token like any password login."""
    admin = await resolve_admin(request, persist_roles=True)  # syncs the Keycloak-mapped RBAC roles
    token, _ = await create_token(admin, name="admin-oidc")
    return TokenOut(token=token)
