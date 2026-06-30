"""Admin authentication via OIDC (Keycloak).

The Vue admin runs the Keycloak auth-code flow and sends the issued JWT as ``Authorization:
Bearer <jwt>``. We validate it against the realm JWKS (arvel ``OidcGuard`` + ``jwks_verifier``),
require the configured Keycloak realm role, and just-in-time provision a local admin ``User`` keyed
by the stable OIDC subject. The verifier is resolved from the ``admin_oidc_guard`` container binding
so a test can swap in a fake (no live Keycloak needed).
"""

from typing import Any, cast

from arvel import abort
from arvel.http import Request
from arvel.kernel import app
from arvel.support.facades import Config

from app.enums import UserRole
from app.models.user import User


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


async def resolve_admin(request: Request) -> User:
    """Authenticate + authorize an admin from the request's OIDC bearer token, JIT-provisioning a
    local admin User. 401 if the token is missing/invalid; 403 if it lacks the admin realm role."""
    guard = app("admin_oidc_guard")
    principal = await guard.verify(request)
    if principal is None:
        abort(401, "Invalid or missing OIDC token.")

    admin_role = Config.get("auth.oidc")["admin_role"]
    claims = cast("dict[str, Any]", dict(principal.claims))
    if admin_role not in _realm_roles(claims):
        abort(403, "This account is not an administrator.")

    # JIT provisioning: find the local admin by email (Keycloak is the source of truth), else create.
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
    return user
