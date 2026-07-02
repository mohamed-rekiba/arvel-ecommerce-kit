"""Integration tier — the kit against REAL services via testcontainers (S1).

Every test here boots the kit through its production bootstrap (`create_app`) with env pointing at
throwaway containers, and drives the relevant **arvel module** through that boot — no bespoke
harnesses, no infra mocks. The tier is opt-in (`pytest -m integration` / `make test-integration`);
the default lane stays hermetic. Skips cleanly when Docker is unavailable.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("testcontainers.core.generic")


def _docker_available() -> bool:
    try:
        import docker
    except ImportError:
        return False
    try:
        docker.from_env().ping()
    except Exception:
        return False
    return True


_DOCKER = _docker_available()


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    skip = pytest.mark.skipif(not _DOCKER, reason="Docker not available")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)


# --- containers (session-scoped: one boot per service per run) -----------------------------------


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    """A throwaway Postgres (same major as compose), as an asyncpg URL."""
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:18-alpine", driver="asyncpg") as pg:
        yield pg.get_connection_url()


@pytest.fixture(scope="session")
def valkey_url() -> Iterator[str]:
    """A throwaway Valkey (Redis-wire-compatible — see DR use-rustfs-not-minio's sibling rule:
    Valkey, not Redis), as a redis:// URL."""
    from testcontainers.core.generic import DockerContainer
    from testcontainers.core.wait_strategies import LogMessageWaitStrategy

    container = (
        DockerContainer("valkey/valkey:9-alpine")
        .with_exposed_ports(6379)
        .waiting_for(
            LogMessageWaitStrategy("Ready to accept connections").with_startup_timeout(
                30
            )
        )
    )
    with container:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(6379)
        yield f"redis://{host}:{port}/0"


@pytest.fixture(scope="session")
def rabbitmq_url() -> Iterator[str]:
    """A throwaway RabbitMQ, as an amqp:// URL (any AMQP broker — LavinMQ works the same)."""
    from testcontainers.core.generic import DockerContainer
    from testcontainers.core.wait_strategies import LogMessageWaitStrategy

    container = (
        DockerContainer("rabbitmq:4-alpine")
        .with_exposed_ports(5672)
        .waiting_for(
            LogMessageWaitStrategy("Server startup complete").with_startup_timeout(90)
        )
    )
    with container:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(5672)
        yield f"amqp://guest:guest@{host}:{port}/"


@pytest.fixture(scope="session")
def rustfs_s3() -> Iterator[dict[str, str]]:
    """A throwaway RustFS; yields endpoint + credentials for the s3 disk (bucket NOT created)."""
    import s3fs
    from testcontainers.core.generic import DockerContainer
    from testcontainers.core.wait_strategies import LogMessageWaitStrategy

    container = (
        DockerContainer("rustfs/rustfs:latest")
        .with_env("RUSTFS_ACCESS_KEY", "arvel")
        .with_env("RUSTFS_SECRET_KEY", "arvelsecret")
        .with_env("RUSTFS_VOLUMES", "/data")
        .with_exposed_ports(9000)
        .waiting_for(LogMessageWaitStrategy("Starting:").with_startup_timeout(60))
    )
    with container:
        endpoint = f"http://{container.get_container_host_ip()}:{container.get_exposed_port(9000)}"
        creds = {"endpoint": endpoint, "key": "arvel", "secret": "arvelsecret"}
        probe = s3fs.S3FileSystem(
            key=creds["key"],
            secret=creds["secret"],
            client_kwargs={"endpoint_url": endpoint},
        )
        for _ in range(60):  # the entrypoint logs "Starting:" before the API binds
            try:
                probe.ls("")
                break
            except Exception:
                time.sleep(0.5)
        yield creds


@pytest.fixture(scope="session")
def meilisearch() -> Iterator[dict[str, str]]:
    """A throwaway Meilisearch; yields {url, key}. Readiness = the /health endpoint answers."""
    import httpx
    from testcontainers.core.generic import DockerContainer

    key = "integration-master-key"
    container = (
        DockerContainer("getmeili/meilisearch:v1.48")
        .with_env("MEILI_MASTER_KEY", key)
        .with_env("MEILI_ENV", "development")
        .with_exposed_ports(7700)
    )
    with container:
        url = f"http://{container.get_container_host_ip()}:{container.get_exposed_port(7700)}"
        for _ in range(120):
            try:
                if httpx.get(f"{url}/health").json().get("status") == "available":
                    break
            except Exception:
                pass
            time.sleep(0.5)
        else:
            raise RuntimeError("Meilisearch container never became available")
        yield {"url": url, "key": key}


@pytest.fixture(scope="session")
def keycloak_issuer() -> Iterator[str]:
    """A throwaway Keycloak with the kit's `arvel` realm imported; yields the realm issuer URL."""
    import httpx
    from testcontainers.core.generic import DockerContainer
    from testcontainers.core.wait_strategies import LogMessageWaitStrategy

    realm = str(
        Path(__file__).resolve().parents[2]
        / ".docker"
        / "keycloak"
        / "realm-export.json"
    )
    container = (
        DockerContainer("quay.io/keycloak/keycloak:26.6")
        .with_env("KC_BOOTSTRAP_ADMIN_USERNAME", "admin")
        .with_env("KC_BOOTSTRAP_ADMIN_PASSWORD", "admin")
        .with_volume_mapping(realm, "/opt/keycloak/data/import/realm-export.json")
        .with_command("start-dev --import-realm")
        .with_exposed_ports(8080)
        .waiting_for(
            LogMessageWaitStrategy("Running the server").with_startup_timeout(180)
        )
    )
    with container:
        base = f"http://{container.get_container_host_ip()}:{container.get_exposed_port(8080)}"
        issuer = f"{base}/realms/arvel"
        for _ in range(120):  # the realm import completes after the server banner
            try:
                if httpx.get(issuer).status_code == 200:
                    break
            except Exception:
                pass
            time.sleep(0.5)
        else:
            raise RuntimeError("Keycloak realm never became available")
        yield issuer


@pytest.fixture(scope="session")
def mailpit() -> Iterator[dict[str, Any]]:
    """A throwaway Mailpit; yields {host, smtp_port, api} (SMTP :1025, HTTP API :8025)."""
    import httpx
    from testcontainers.core.generic import DockerContainer

    container = DockerContainer("axllent/mailpit:latest").with_exposed_ports(1025, 8025)
    with container:
        host = container.get_container_host_ip()
        api = f"http://{host}:{container.get_exposed_port(8025)}"
        for _ in range(60):
            try:
                if httpx.get(f"{api}/api/v1/info").status_code == 200:
                    break
            except Exception:
                pass
            time.sleep(0.5)
        else:
            raise RuntimeError("Mailpit API never became available")
        yield {"host": host, "smtp_port": container.get_exposed_port(1025), "api": api}


# --- kit boot helper ------------------------------------------------------------------------------


@pytest.fixture
def kit_app(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Boot the kit through the production bootstrap with env overrides, migrations applied.

    Returns (TestClient factory): call with env overrides; DATABASE_URL defaults to a migrated tmp
    sqlite file so non-DB service tests don't need Postgres. The client context manages app
    startup/shutdown exactly like the served path.
    """
    from litestar.testing import TestClient

    from arvel.database import ConnectionResolver, Migrator, discover_migrations

    def _boot(**env: str) -> TestClient[Any]:
        url = env.pop("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'kit.sqlite'}")
        monkeypatch.setenv("DATABASE_URL", url)
        for key, value in env.items():
            monkeypatch.setenv(key, value)

        async def _migrate() -> None:
            db = ConnectionResolver({"default": {"url": url}})
            await Migrator(db).run(discover_migrations(["database/migrations"]))
            await db.dispose()

        asyncio.run(_migrate())
        from bootstrap.app import create_app

        return TestClient(app=create_app().as_asgi())

    return _boot
