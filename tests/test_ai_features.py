"""arvel-ai through the served path: the admin copy-draft endpoint (gateway +
AI.fake()) and the MCP server (401 challenge, tools/list, tools/call) — the
consumer-path evidence for the arvel-ai v1 merge gate."""

import asyncio

import pytest
from litestar.testing import TestClient

from arvel.database import ConnectionResolver, Migrator, discover_migrations

from arvel_ai import AI

from app.enums import ProductStatus, UserRole
from app.models.category import Category
from app.models.product import Product
from app.models.user import User
from tests.rbac_helpers import seed_rbac


@pytest.fixture
def client(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'ai.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("FILESYSTEM_LOCAL_ROOT", str(tmp_path / "media"))
    monkeypatch.setenv("MCP_TOKEN", "kit-test-mcp-token")

    async def seed() -> None:
        db = ConnectionResolver({"default": {"url": url}})
        await Migrator(db).run(discover_migrations(["database/migrations"]))
        await seed_rbac(db)
        models = (User, Category, Product)
        for model in models:
            model.set_connection(db)
        admin = await User.create(
            name="Ada",
            email="admin@example.com",
            password="secret-admin",
            role=UserRole.ADMIN,
        )
        await admin.assign_role("super-admin")
        cat = await Category.create(
            translations={"en": {"name": "Gear"}}, slug="gear", published=True
        )
        await Product.create(
            category_id=cat.id,
            translations={"en": {"name": "Wool Socks"}},
            slug="wool-socks",
            price_cents=1299,
            currency="USD",
            status=ProductStatus.ACTIVE,
            published=True,
        )
        for model in models:
            model.set_connection(None)
        await db.dispose()

    asyncio.run(seed())
    from bootstrap.app import create_app

    with TestClient(app=create_app().as_asgi()) as test_client:
        yield test_client
    AI.clear_swapped()


def _admin(client):
    token = client.post(
        "/api/login", json={"email": "admin@example.com", "password": "secret-admin"}
    ).json()["token"]
    return {"Authorization": f"Bearer {token}"}


# ---- gateway feature: admin copy draft ---------------------------------------


def test_copy_draft_via_gateway(client) -> None:
    fake = AI.fake()
    fake.replies = ['{"title": "Warm Wool Socks", "bullets": ["Soft", "Durable", "Fair price"]}']

    out = client.post("/api/admin/products/wool-socks/copy-draft", headers=_admin(client))
    assert out.status_code == 200, out.text
    body = out.json()
    assert body["title"] == "Warm Wool Socks"
    assert len(body["bullets"]) == 3
    # the gateway received the product's real name; the faked path records the
    # alias as-passed (resolution is the manager's job, unit-tested in arvel-ai)
    fake.assert_chatted("Wool Socks")
    assert fake.requests[-1].model == "fast"
    assert fake.requests[-1].response_schema is not None


def test_copy_draft_requires_admin(client) -> None:
    assert client.post("/api/admin/products/wool-socks/copy-draft").status_code == 401


# ---- MCP server through the served path ---------------------------------------


def test_mcp_unauthenticated_gets_spec_challenge(client) -> None:
    out = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert out.status_code == 401
    challenge = out.headers.get("www-authenticate", "")
    assert 'resource_metadata="' in challenge
    assert challenge.startswith("Bearer ")


def test_mcp_metadata_document_is_public(client) -> None:
    doc = client.get("/.well-known/oauth-protected-resource").json()
    assert doc["resource"].endswith("/mcp")
    assert doc["bearer_methods_supported"] == ["header"]


def test_mcp_tools_list_and_call(client) -> None:
    headers = {"Authorization": "Bearer kit-test-mcp-token"}
    listed = client.post(
        "/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, headers=headers
    ).json()
    assert any(t["name"] == "product_status" for t in listed["result"]["tools"])

    called = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "product_status", "arguments": {"slug": "wool-socks"}},
        },
        headers=headers,
    ).json()
    assert called["result"]["isError"] is False
    assert "wool-socks" in called["result"]["content"][0]["text"]

    missing = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "product_status", "arguments": {"slug": "nope"}},
        },
        headers=headers,
    ).json()
    assert "not found" in missing["result"]["content"][0]["text"]
