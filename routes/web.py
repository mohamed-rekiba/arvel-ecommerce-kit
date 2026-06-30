"""Web routes — stateful, browser-facing pages (the "web" group)."""

from typing import Any

from arvel import Route, view
from arvel.http import Request


async def home(request: Request) -> Any:
    """The welcome page."""
    # Render resources/views/welcome.html (Jinja2) with data, as an HTML response.
    return await view(
        "welcome",
        {"title": "arvel-ecommerce-kit", "tagline": "Your arvel app is running."},
    ).to_response()


Route.get("/", home, name="home")
