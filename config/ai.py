"""AI gateway (arvel-ai) — driver, model aliases, and the MCP server.

Provider keys live in env vars only. The storefront's default driver speaks any
OpenAI-compatible endpoint (a LiteLLM proxy, vLLM, ...) named by AI_GATEWAY_URL;
tests swap in the fake driver via AI.fake().
"""

from arvel import env

config = {
    "default": env("AI_DRIVER", "openai_compatible"),
    # aliases — the churn shield: code says "fast"/"smart", ops picks models here
    "models": {
        "fast": env("AI_MODEL_FAST", "claude-haiku-4-5"),
        "smart": env("AI_MODEL_SMART", "claude-opus-4-8"),
    },
    "drivers": {
        "openai_compatible": {
            "base_url": env("AI_GATEWAY_URL", None),
            "api_key_env": "AI_API_KEY",
            "model": env("AI_MODEL_FAST", "claude-haiku-4-5"),
        },
    },
    # MCP server: agents can query product status (see app/mcp_tools.py).
    "mcp": {
        "enabled": True,
        "path": "/mcp",
        "public_url": env("APP_URL", "http://localhost:8000"),
        "tools": ["app.mcp_tools"],
        "auth": {"mode": "token", "token_env": "MCP_TOKEN"},
    },
}
