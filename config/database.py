"""Database config — connections + the default connection.

The kit runs on **PostgreSQL** (see docker-compose.yml — `docker compose up -d db`). `DATABASE_URL`
sets the connection; the driver is inferred from the URL scheme, so the test suite can point it at
an in-process sqlite file while the app + `arvel migrate`/`db:seed`/`serve` use Postgres.
"""

from arvel import env

config = {
    "default": "default",
    "connections": {
        "default": {
            "url": env(
                "DATABASE_URL",
                "postgresql+asyncpg://arvel:arvel@localhost:5432/arvel_ecommerce_kit",
            ),
        },
    },
}
