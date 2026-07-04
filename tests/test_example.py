"""Example feature test — the app serves its home route (run with ``pytest``).

"/" is served by with_public_dir(...) from the built Vue SPA's index.html, so this test doesn't
depend on `make front` having run first — it plants a placeholder if the real build is missing,
and cleans up only what it planted.
"""

from pathlib import Path

from litestar.testing import TestClient

from asgi import asgi_app

_PUBLIC = Path(__file__).resolve().parent.parent / "public"
_INDEX = _PUBLIC / "index.html"


def test_home_returns_200() -> None:
    planted_dir = not _PUBLIC.exists()
    planted_index = not _INDEX.exists()
    if planted_index:
        _PUBLIC.mkdir(exist_ok=True)
        _INDEX.write_text("<html>placeholder — see make front</html>")
    try:
        with TestClient(app=asgi_app) as client:
            assert client.get("/").status_code == 200
    finally:
        if planted_index:
            _INDEX.unlink()
        if planted_dir:
            _PUBLIC.rmdir()
