"""Web routes — stateful, browser-facing pages (the "web" group)."""

from arvel import Route, view


async def home(request):
    # Render resources/views/welcome.html (Jinja2) with data, as an HTML response.
    return await view("welcome", {"title": "arvel-ecommerce-kit", "tagline": "Your arvel app is running."}).to_response()


Route.get("/", home, name="home")
