"""Admin OIDC (Keycloak) — the admin authenticates with a Keycloak-issued JWT (Authorization:
Bearer). arvel's OidcGuard validates it and exposes the claims; we require the admin realm role and
JIT-provision a local admin User. The JWKS verifier is faked here (an injected ClaimsVerifier) so no
live Keycloak is needed; the real-Keycloak-container proof lives in the integration tier.
"""

import asyncio

import pytest
from litestar.testing import TestClient

from arvel.auth.oidc import OidcGuard
from arvel.database import ConnectionResolver, Migrator, discover_migrations

# claims a real Keycloak token would carry (admin has the realm role; the customer does not)
_ADMIN_CLAIMS = {
    "sub": "kc-admin-001",
    "email": "boss@shop.test",
    "name": "Boss Admin",
    "realm_access": {"roles": ["admin", "catalog-manager", "offline_access"]},
}
_USER_CLAIMS = {
    "sub": "kc-user-002",
    "email": "nimda@shop.test",
    "realm_access": {"roles": ["offline_access"]},
}


async def _fake_verifier(token: str):
    return {"admin-jwt": _ADMIN_CLAIMS, "user-jwt": _USER_CLAIMS}.get(token)


@pytest.fixture
def client(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'oidc.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", url)

    async def migrate() -> None:
        from arvel.auth import Permission as PermissionModel
        from arvel.auth import Role

        from tests.rbac_helpers import seed_rbac

        db = ConnectionResolver({"default": {"url": url}})
        await Migrator(db).run(discover_migrations(["database/migrations"]))
        await seed_rbac(db)  # roles/permissions must exist for the OIDC→bearer role sync (DR-0030)
        for model in (Role, PermissionModel):
            model.set_connection(None)  # reset so the served app uses its own connection
        await db.dispose()

    asyncio.run(migrate())

    from bootstrap.app import create_app

    app = create_app()
    # swap the production JWKS guard for one with a fake verifier (no live Keycloak needed)
    app.instance("admin_oidc_guard", OidcGuard(_fake_verifier, provider="keycloak"))
    with TestClient(app=app.as_asgi()) as test_client:
        yield test_client


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_admin_token_provisions_and_returns_identity(client) -> None:
    resp = client.get("/api/admin/me", headers=_bearer("admin-jwt"))
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "boss@shop.test"
    assert body["role"] == "admin"
    # a second call reuses the JIT-provisioned admin (no duplicate)
    again = client.get("/api/admin/me", headers=_bearer("admin-jwt"))
    assert again.json()["id"] == body["id"]


def test_non_admin_role_is_forbidden(client) -> None:
    assert client.get("/api/admin/me", headers=_bearer("user-jwt")).status_code == 403


def test_missing_or_invalid_token_is_unauthorized(client) -> None:
    assert client.get("/api/admin/me").status_code == 401
    assert client.get("/api/admin/me", headers=_bearer("garbage")).status_code == 401


def test_claim_map_maps_keycloak_realm_roles_to_arvel_roles() -> None:
    """The Keycloak realm-role claim → arvel RBAC role names (safe-by-default: unmapped → nothing)."""
    from arvel.auth.claim_map import roles_for_claims

    from app.auth.admin_oidc import ROLE_CLAIM_MAP

    claims = {"realm_access": {"roles": ["catalog-manager", "admin", "offline_access"]}}
    mapped = roles_for_claims(
        claims, ROLE_CLAIM_MAP, claim_paths=("realm_access.roles",)
    )
    assert mapped == {
        "catalog-manager"
    }  # "admin"/"offline_access" aren't RBAC roles → dropped


def test_oidc_exchange_issues_bearer_with_synced_roles(client) -> None:
    """DR-0030: a Keycloak token → an arvel bearer PAT that carries the claim-mapped RBAC roles, so it
    works against the bearer-guarded admin APIs. The 'catalog-manager' realm role syncs to catalog.*."""
    exchange = client.post("/api/admin/oidc/token", headers=_bearer("admin-jwt"))
    assert exchange.status_code == 200
    bearer = exchange.json()["token"]

    # the issued bearer can read the admin catalog (catalog.view via the synced catalog-manager role)
    assert client.get("/api/admin/products", headers=_bearer(bearer)).status_code == 200

    # a non-admin Keycloak token cannot exchange (403), and no token is 401
    assert client.post("/api/admin/oidc/token", headers=_bearer("user-jwt")).status_code == 403
    assert client.post("/api/admin/oidc/token").status_code == 401
