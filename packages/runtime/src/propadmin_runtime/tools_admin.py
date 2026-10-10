"""Admin-only MCP tools: the whole /v1 admin API, served only to admin-scoped grants."""

import json

import httpx

from .auth import issue_token

# Token minting, auth, live streams and the admin chat itself stay out of the agent's reach.
BLOCKED = ("/v1/auth/", "/v1/mcp/tokens", "/v1/admin-chat")
METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"]

TOOLS = {
    "list_admin_endpoints": {
        "description": "List every admin API endpoint (method, path, summary) callable via "
        "admin_api. Optionally filter by a path substring.",
        "input_schema": {
            "type": "object",
            "properties": {"filter": {"type": "string", "minLength": 1, "maxLength": 200}},
            "required": [],
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": True, "destructiveHint": False,
                        "idempotentHint": True, "openWorldHint": False},
    },
    "admin_api": {
        "description": "Call one admin panel API endpoint as the administrator: rules, entity "
        "types, settings, providers, ledgers, skills and proposals, tickets, ingestion, "
        "agent runs, credentials. path starts with /v1/. Mutations need a reason.",
        "input_schema": {
            "type": "object",
            "properties": {
                "method": {"type": "string", "minLength": 1, "maxLength": 10},
                "path": {"type": "string", "minLength": 4, "maxLength": 2000},
                "query": {"type": "object", "additionalProperties": True},
                "body": {"type": "object", "additionalProperties": True},
                "reason": {"type": "string", "minLength": 1, "maxLength": 2000},
            },
            "required": ["method", "path"],
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": True,
                        "idempotentHint": False, "openWorldHint": False},
    },
}


def endpoints(app, needle=None):
    return [
        {"method": method.upper(), "path": path, "summary": operation.get("summary", "")}
        for path, operations in app.openapi()["paths"].items()
        if path.startswith("/v1/") and not path.startswith(BLOCKED)
        and not path.endswith("/stream") and (not needle or needle in path)
        for method, operation in operations.items()
    ]


async def call(app, name, args):
    if name == "list_admin_endpoints":
        return {"items": endpoints(app, args.get("filter"))}
    method, path = args["method"].upper(), args["path"]
    if method not in METHODS:
        raise ValueError(f"method must be one of {', '.join(METHODS)}")
    if not path.startswith("/v1/") or path.startswith(BLOCKED) or path.endswith("/stream"):
        raise ValueError("path must be an admin /v1/ endpoint from list_admin_endpoints")
    if ".." in path or "?" in path or "#" in path:
        raise ValueError("Pass query parameters in query, not in path")
    if method != "GET" and not args.get("reason", "").strip():
        raise ValueError("Admin API mutations need a reason")
    token = issue_token(app.state.settings, "admin", 300)
    # In-process ASGI call: same validation, auth and audit as the admin panel, no network hop.
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://admin-agent", timeout=120
    ) as client:
        response = await client.request(
            method,
            path,
            params=args.get("query"),
            json=args.get("body") if method != "GET" else None,
            headers={"Authorization": f"Bearer {token}"},
        )
    try:
        data = response.json()
    except json.JSONDecodeError:
        data = response.text[:20000]
    if response.status_code >= 400:
        detail = data.get("detail", data) if isinstance(data, dict) else data
        raise ValueError(f"HTTP {response.status_code}: {json.dumps(detail)[:4000]}")
    return {"status": response.status_code, "data": data}
