"""OpenAPI / API-docs configuration — bearer-token auth enabled (the --auth scaffold).

The ``security`` bearer scheme gives the docs UI an 'Authorize' button so you can paste an access token
and call protected endpoints. Routes that require it are marked with ``.secure("bearer")`` (see
routes/api.py — GET /api/user). See app/config/openapi.py comments for the full set of options.
"""

from arvel import env

config = {
    "title": env("APP_NAME", "arvel-ecommerce-kit"),
    "version": "0.1.0",
    "description": "The arvel-ecommerce-kit API.",
    "path": "/docs",  # docs UI here; raw document at /docs/openapi.json
    "ui": "swagger",  # swagger | redoc | scalar | rapidoc | stoplight
    "use_handler_docstrings": True,
    "security": {
        "bearer": {
            "format": "JWT",
            "description": "Customer token from POST /api/login",
        },
        "oidc": {
            "openIdConnectUrl": env("OIDC_ISSUER", "http://localhost:8080/realms/arvel")
            + "/.well-known/openid-configuration",
            "description": "Admin sign-in via Keycloak (OIDC)",
        },
    },
}
