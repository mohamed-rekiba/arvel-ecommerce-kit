"""Authentication config — guards + their drivers.

The `api` guard uses bearer tokens (arvel.auth personal access tokens); the `web` guard uses
session cookies.

Admins authenticate via OIDC against Keycloak: the Vue admin runs the auth-code flow at Keycloak,
then sends the issued JWT as `Authorization: Bearer <jwt>`; arvel validates it against the realm's
JWKS (`auth.oidc`). Point OIDC_ISSUER/OIDC_JWKS_URI/OIDC_AUDIENCE at your Keycloak realm + client.
"""

from arvel import env

_REALM = env("OIDC_ISSUER", "http://localhost:8080/realms/arvel")

config = {
    "defaults": {"guard": "api"},
    "guards": {
        "api": {"driver": "token"},
        "web": {"driver": "session"},
        "oidc": {"driver": "oidc"},
    },
    "oidc": {
        "issuer": _REALM,
        "jwks_uri": env("OIDC_JWKS_URI", f"{_REALM}/protocol/openid-connect/certs"),
        "audience": env("OIDC_AUDIENCE", "arvel-admin"),
        "provider": "keycloak",
        # the Keycloak realm role that grants admin access (mapped from realm_access.roles)
        "admin_role": env("OIDC_ADMIN_ROLE", "admin"),
    },
}
