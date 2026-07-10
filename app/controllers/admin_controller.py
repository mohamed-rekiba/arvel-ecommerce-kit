"""Admin endpoints authenticated via OIDC (Keycloak), distinct from the customer token flow."""

from arvel.auth.tokens import create_token
from arvel.http import Request

from app.auth.admin_oidc import resolve_admin
from app.schemas import AdminMeOut, TokenOut


async def me(request: Request) -> AdminMeOut:
    """The current admin's identity, resolved from the Keycloak OIDC token (401 without a valid
    token, 403 without the admin realm role)."""
    admin = await resolve_admin(request)
    return AdminMeOut(
        id=admin.id,
        name=admin.name,
        email=admin.email,
        role=admin.role.value,  # cast by User.__casts__
    )


async def oidc_exchange(request: Request) -> TokenOut:
    """Exchange a validated Keycloak token for an arvel bearer PAT. JIT-provisions the admin and
    persists the Keycloak-mapped RBAC roles so the issued bearer carries them into the
    bearer-guarded admin APIs."""
    admin = await resolve_admin(request, persist_roles=True)
    token, _ = await create_token(admin, name="admin-oidc")
    return TokenOut(token=token)
