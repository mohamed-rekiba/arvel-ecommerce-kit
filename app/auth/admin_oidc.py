"""Admin authentication via OIDC (Keycloak).

Validates the bearer JWT against the realm JWKS, requires the configured admin realm role, and
JIT-provisions a local admin ``User`` keyed by the OIDC subject. The verifier is resolved from the
``admin_oidc_guard`` container binding so a test can swap in a fake.
"""

from typing import Any, cast

from arvel import abort
from arvel.http import Request
from arvel.kernel import app
from arvel.support.facades import Config

from app.enums import RoleName, UserRole
from app.models.user import User

# Keycloak realm role → arvel RBAC role. Safe-by-default: a Keycloak role absent here grants nothing.
ROLE_CLAIM_MAP: dict[str, str] = {r.value: r.value for r in RoleName}


def build_admin_oidc_guard() -> Any:
    """Build the production OIDC guard from ``auth.oidc`` config (validates against Keycloak JWKS)."""
    from arvel.auth.oidc import OidcGuard, jwks_verifier

    cfg = Config.get("auth.oidc")
    verifier = jwks_verifier(
        jwks_uri=cfg["jwks_uri"], issuer=cfg["issuer"], audience=cfg["audience"]
    )
    return OidcGuard(verifier, provider=cfg.get("provider", "oidc"))


def _realm_roles(claims: dict[str, Any]) -> list[str]:
    """Keycloak realm roles live under ``realm_access.roles``."""
    realm_access = claims.get("realm_access")
    if not isinstance(realm_access, dict):
        return []
    roles = cast("dict[str, Any]", realm_access).get("roles")
    if not isinstance(roles, list):
        return []
    return [str(r) for r in cast("list[Any]", roles)]


async def resolve_admin(request: Request, *, persist_roles: bool = False) -> User:
    """Authenticate + authorize an admin from the OIDC bearer token, JIT-provisioning a local admin
    User. 401 if the token is missing/invalid, 403 if it lacks the admin realm role. With
    ``persist_roles=True`` the mapped roles are written to RBAC membership instead of being carried
    as ephemeral, request-scoped grants."""
    guard = app("admin_oidc_guard")
    principal = await guard.verify(request)
    if principal is None:
        abort(401, "Invalid or missing OIDC token.")

    admin_role = Config.get("auth.oidc")["admin_role"]
    claims = cast("dict[str, Any]", dict(principal.claims))
    if admin_role not in _realm_roles(claims):
        abort(403, "This account is not an administrator.")

    # JIT-provision by email; Keycloak is the source of truth.
    email = principal.email or f"{principal.subject}@oidc.local"
    user = await User.where("email", email).first()
    if user is None:
        user = await User.create(
            name=claims.get("name", email),
            email=email,
            password=principal.subject,  # unused for OIDC admins; never a login credential
            role=UserRole.ADMIN,
        )
    elif user.role is not UserRole.ADMIN:
        user.role = UserRole.ADMIN  # promote: Keycloak says they're an admin
        await user.save()

    # Map Keycloak realm roles → arvel RBAC roles via claim_map.
    from arvel.auth.claim_map import roles_for_claims

    idp_roles = roles_for_claims(
        claims, ROLE_CLAIM_MAP, claim_paths=("realm_access.roles",)
    )
    if persist_roles:
        # Reconcile to the exact claim set so a Keycloak demotion actually revokes access;
        # other RBAC roles the user holds are left untouched.
        managed = {role_name.value for role_name in RoleName}
        existing = {role.name for role in await user.roles()}
        for role_name in idp_roles - existing:
            await user.assign_role(role_name)
        for role_name in (existing & managed) - idp_roles:
            await user.remove_role(role_name)
    else:
        # Ephemeral, request-scoped grants — no membership written.
        user.set_idp_roles(idp_roles)
    return cast("User", user)
