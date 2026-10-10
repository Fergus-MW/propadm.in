"""The API's single, authenticated, graph-only Streamable HTTP MCP gateway."""

import json
import math
import re
import time
from typing import Literal
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from propadmin_core import ConflictError, ProviderNotConfigured
from propadmin_core.store import identifier, now, publish
from propadmin_core.ticket_completion import COMPLETION_INSTRUCTIONS
from pydantic import Field

from . import (
    routes_agent,
    routes_browser,
    routes_email,
    routes_voice,
    routes_workflow,
    tools_admin,
    tools_ledger,
    tools_portal,
)
from .auth import issue_token, require_admin, require_internal, require_session
from .models import Input
from .observability import current_ids

router = APIRouter()
VERSIONS = ("2026-07-28", "2025-11-25")
LEGACY = "2025-11-25"
PROTOCOL_KEY = "io.modelcontextprotocol/protocolVersion"
SERVER_INFO = {"name": "propadmin-graph", "version": "0.1.0"}
INSTRUCTIONS = (
    "Use this single endpoint for every graph read and write. Read entity versions before "
    "writes; re-read on conflicts. Supply a reason for mutations. Rules are admin-only. "
    "Local mode does not execute raw SurrealQL or external communications. "
    "Property managers can pause or take over work. Honour portal controls; use get_portal_item "
    "and draft_portal_reply for human review instead of sending when an action is blocked."
    " " + COMPLETION_INSTRUCTIONS
)


def string(max_length=4000, **extra):
    return {"type": "string", "minLength": 1, "maxLength": max_length, **extra}


def integer(minimum=1, maximum=2**53 - 1):
    return {"type": "integer", "minimum": minimum, "maximum": maximum}


def array(items):
    return {"type": "array", "items": items, "maxItems": 100}


def object_schema(properties=None, required=(), *, additional=False):
    return {
        "type": "object",
        "properties": properties or {},
        "required": list(required),
        "additionalProperties": additional,
    }


ID = string(500)
REASON = string(2000)
FIELDS = object_schema(additional=True)
WRITE_FIELDS = {
    "name": string(500),
    "description": {"type": "string", "maxLength": 100_000},
    "aliases": array(string(500)),
    "fields": FIELDS,
    "external_ids": {"type": "object", "additionalProperties": {"type": "string"}},
}


def tool(name, description, properties, required=(), *, read=False, destructive=False):
    return {
        "name": name,
        "description": description,
        "inputSchema": object_schema(properties, required),
        "annotations": {
            "readOnlyHint": read,
            "destructiveHint": destructive,
            "idempotentHint": read,
            "openWorldHint": False,
        },
    }


TOOLS = [
    tool(
        "search",
        "Hybrid local/provider search with source citations.",
        {
            "query": string(2000),
            "types": array(string(100)),
            "limit": integer(1, 100),
            "expand": {"type": "boolean"},
        },
        ["query"],
        read=True,
    ),
    tool(
        "get_entity",
        "Read typed fields, evidence, edges, version and change history.",
        {"id": ID},
        ["id"],
        read=True,
    ),
    tool(
        "traverse",
        "Return an entity neighbourhood, at most five hops.",
        {"entity_id": ID, "depth": integer(0, 5), "type": string(100)},
        ["entity_id"],
        read=True,
    ),
    tool(
        "get_document",
        "Read the source document, chunks, mentions and facts.",
        {"id": ID},
        ["id"],
        read=True,
    ),
    tool(
        "query_graph",
        "Read-only SurrealQL; explicitly unavailable with the local JSON store.",
        {"query": string(8000)},
        ["query"],
        read=True,
    ),
    tool(
        "upsert_entity",
        "Create an entity, or update the explicit id with its current version. "
        + COMPLETION_INSTRUCTIONS,
        {**WRITE_FIELDS, "id": ID, "type": string(100), "version": integer(), "reason": REASON},
        ["type", "name", "reason"],
    ),
    tool(
        "update_entity",
        "Update declared entity fields using optimistic concurrency. " + COMPLETION_INSTRUCTIONS,
        {**WRITE_FIELDS, "id": ID, "version": integer(), "reason": REASON},
        ["id", "version", "reason"],
    ),
    tool(
        "link_entities",
        "Create a manual relation between two canonical entities.",
        {
            "source": ID,
            "target": ID,
            "relation": string(100, pattern=r"^[a-z][a-z0-9_]*$"),
            "attributes": {"type": "object", "additionalProperties": True},
            "reason": REASON,
        },
        ["source", "target", "relation", "reason"],
    ),
    tool(
        "unlink_entities",
        "Remove a manual edge; rule-generated edges are protected.",
        {"id": ID, "reason": REASON},
        ["id", "reason"],
        destructive=True,
    ),
    tool(
        "merge_entities",
        "Merge two entities with current source and target versions.",
        {
            "id": ID,
            "target_id": ID,
            "version": integer(),
            "target_version": integer(),
            "reason": REASON,
        },
        ["id", "target_id", "version", "target_version", "reason"],
        destructive=True,
    ),
    tool(
        "add_note",
        "Append an embedded note to a type declaring an array<text> notes field.",
        {"id": ID, "note": string(20_000), "version": integer(), "reason": REASON},
        ["id", "note", "version", "reason"],
    ),
]
# Comms, browser, plan and skill tools live beside their routes; one endpoint serves all.
EXTENSIONS = {
    name: entry
    for module in (
        routes_agent,
        routes_voice,
        routes_email,
        routes_browser,
        routes_workflow,
        tools_ledger,
        tools_portal,
    )
    for name, entry in module.TOOLS.items()
}
# These handlers write their own record_action entry; /mcp must not audit them twice.
SELF_LOGGED = {
    name
    for module in (routes_agent, routes_voice, routes_email, routes_browser)
    for name in module.TOOLS
}
TOOLS += [
    {
        "name": name,
        "description": entry["description"],
        "inputSchema": entry["input_schema"],
        **({"annotations": entry["annotations"]} if "annotations" in entry else {}),
    }
    for name, entry in EXTENSIONS.items()
]
CATALOGUE = {item["name"]: item for item in TOOLS}
# Admin chat runs hold an admin-scoped grant: every tool above plus the whole admin API.
ADMIN_TOOLS = [
    {
        "name": name,
        "description": entry["description"],
        "inputSchema": entry["input_schema"],
        "annotations": entry["annotations"],
    }
    for name, entry in tools_admin.TOOLS.items()
]
ADMIN_CATALOGUE = {**CATALOGUE, **{item["name"]: item for item in ADMIN_TOOLS}}


def is_admin(request, session_id):
    grant = request.app.state.store.snapshot().get("mcp_sessions", {}).get(session_id, {})
    return grant.get("scope") == "admin"


def validate(value, schema, path="arguments"):
    """Validate the small inline schema vocabulary advertised by this gateway."""
    kind = schema.get("type")
    checks = {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": type(value) is int,
        "boolean": type(value) is bool,
        "number": type(value) in {int, float} and math.isfinite(value),
    }
    if kind and not checks.get(kind, False):
        raise ValueError(f"{path} must be {kind}")
    if kind == "object":
        properties = schema.get("properties", {})
        if any(key not in value for key in schema.get("required", [])):
            raise ValueError(f"{path} is missing required fields")
        extra = schema.get("additionalProperties", True)
        if extra is False and set(value) - set(properties):
            raise ValueError(f"{path} contains undeclared fields")
        for key, item in value.items():
            if key in properties:
                validate(item, properties[key], f"{path}.{key}")
            elif isinstance(extra, dict):
                validate(item, extra, path)
    elif kind == "array":
        if len(value) > schema.get("maxItems", 100):
            raise ValueError(f"{path} has too many items")
        for item in value:
            validate(item, schema["items"], path)
    elif kind == "string":
        if not schema.get("minLength", 0) <= len(value) <= schema.get("maxLength", 2_000_000):
            raise ValueError(f"{path} has invalid length")
        if schema.get("minLength") and not value.strip():
            raise ValueError(f"{path} cannot be blank")
        if schema.get("pattern") and not re.fullmatch(schema["pattern"], value):
            raise ValueError(f"{path} has invalid format")
    elif kind in {"integer", "number"}:
        if not schema["minimum"] <= value <= schema["maximum"]:
            raise ValueError(f"{path} is out of range")


def protect_skill(graph, entity_id=None, type_name=None, admin=False):
    if admin:
        return
    if entity_id:
        type_name = graph.get_entity(entity_id)["type"]
    if type_name in {"skill", "skill_version"}:
        raise ValueError("Live skills and their versions can only be changed by an admin")


def execute(request, name, args, session_id, admin=False):
    from .portal_policy import check_agent_control

    check_agent_control(request.app.state.store.snapshot(), session_id, name, args)
    if name in EXTENSIONS:
        return EXTENSIONS[name]["handler"](request.app, session_id, args)
    graph = request.app.state.graph
    actor = f"agent_run:{session_id}"
    reason = args.get("reason", "")
    if name == "search":
        return request.app.state.search.search(args)
    if name == "get_entity":
        return graph.get_entity(args["id"])
    if name == "traverse":
        return graph.graph(args.get("depth", 1), args["entity_id"], args.get("type"))
    if name == "get_document":
        return graph.get_document(args["id"])
    if name == "query_graph":
        raise ProviderNotConfigured(
            "Raw SurrealQL is unavailable with the local JSON repository; "
            "use search, get_entity and traverse. No query was executed."
        )
    if name == "upsert_entity":
        protect_skill(graph, type_name=args["type"], admin=admin)
        payload = {key: value for key, value in args.items() if key != "reason"}
        existing = request.app.state.store.snapshot()["entities"].get(args.get("id"))
        if existing:
            protect_skill(graph, args["id"], admin=admin)
            if existing["type"] != args["type"]:
                raise ValueError("Entity type cannot change during upsert")
            if "version" not in payload:
                raise ValueError("Updating an existing entity requires its current version")
            return graph.update_entity(
                args["id"],
                {k: v for k, v in payload.items() if k not in {"id", "type"}},
                actor,
                reason,
            )
        if "version" in payload:
            raise ConflictError("Entity no longer exists; upsert version cannot create it")
        return graph.create_entity(payload, actor, reason)
    if name == "update_entity":
        protect_skill(graph, args["id"], admin=admin)
        return graph.update_entity(
            args["id"],
            {k: v for k, v in args.items() if k not in {"id", "reason"}},
            actor,
            reason,
        )
    if name == "link_entities":
        protect_skill(graph, args["source"], admin=admin)
        protect_skill(graph, args["target"], admin=admin)
        return graph.link_entities({k: v for k, v in args.items() if k != "reason"}, actor, reason)
    if name == "unlink_entities":
        edge = request.app.state.store.snapshot()["edges"][args["id"]]
        protect_skill(graph, edge["source"], admin=admin)
        protect_skill(graph, edge["target"], admin=admin)
        return graph.unlink_entities(args["id"], actor, reason)
    if name == "merge_entities":
        protect_skill(graph, args["id"], admin=admin)
        protect_skill(graph, args["target_id"], admin=admin)
        return graph.merge_entities(
            args["id"],
            args["target_id"],
            actor,
            reason,
            version=args["version"],
            target_version=args["target_version"],
        )
    if name == "add_note":
        entity = graph.get_entity(args["id"])
        registry = request.app.state.store.snapshot()["entity_types"][entity["type"]]
        if registry["fields"].get("notes", {}).get("type") != "array<text>":
            raise ValueError("This entity type does not declare an array<text> notes field")
        return graph.update_entity(
            args["id"],
            {
                "version": args["version"],
                "fields": {"notes": entity["fields"].get("notes", []) + [args["note"]]},
            },
            actor,
            reason,
        )
    raise ValueError("Unknown graph tool")


def audit(request, session_id, name, args, status, error_code=None):
    """Store metadata only; bearer tokens, tool payloads and documents are never logged here."""
    span_id = current_ids().get("span_id")
    if isinstance(name, str) and name in SELF_LOGGED:
        if span_id and request.app.state.store.read(
            lambda s: any(a.get("span_id") == span_id for a in s["actions"].values())
        ):
            return

    def save(state):
        key = identifier("action")
        state["actions"][key] = {
            "id": key,
            "kind": "mcp.tool",
            "tool": name if isinstance(name, str) and name in ADMIN_CATALOGUE else "unknown",
            "actor": f"agent_run:{session_id}",
            "session_id": session_id,
            "reason": args.get("reason", "") if isinstance(args.get("reason", ""), str) else "",
            "entity_id": args.get("id") or args.get("entity_id") or args.get("source"),
            "status": status,
            "error_code": error_code,
            "created_at": now(),
            "span_id": span_id,
            "reversible": False,
        }
        publish(state, "action.created", {"id": key})

    request.app.state.store.mutate(save)


def rpc_error(request_id, code, message, status=400, data=None):
    error = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return JSONResponse({"jsonrpc": "2.0", "id": request_id, "error": error}, status_code=status)


def result(request_id, payload):
    # 2026-07-28 requires resultType on every result; earlier clients ignore extra keys.
    payload = {"resultType": "complete", **payload}
    return JSONResponse({"jsonrpc": "2.0", "id": request_id, "result": payload})


def transport_error(request, body, params):
    request_id, method = body.get("id"), body["method"]
    accept = request.headers.get("accept", "")
    if "application/json" not in accept or "text/event-stream" not in accept:
        return rpc_error(request_id, -32600, "Accept must include JSON and event-stream", 406)
    version = request.headers.get("mcp-protocol-version")
    if method == "initialize" and not version:
        version = params.get("protocolVersion", LEGACY)
    if version not in VERSIONS:
        return rpc_error(
            request_id,
            -32022,
            "Unsupported protocol version",
            data={
                "supported": list(VERSIONS),
                "requested": version,
            },
        )
    if version == VERSIONS[0] and "id" in body:
        meta = params.get("_meta", {})
        if not isinstance(meta, dict) or meta.get(PROTOCOL_KEY) != version:
            return rpc_error(request_id, -32020, "Header mismatch: protocol metadata")
        if request.headers.get("mcp-method") != method:
            return rpc_error(request_id, -32020, "Header mismatch: Mcp-Method")
        if method == "tools/call" and request.headers.get("mcp-name") != params.get("name"):
            return rpc_error(request_id, -32020, "Header mismatch: Mcp-Name")
    return None


@router.post("/mcp")
async def mcp(request: Request, session_id=Depends(require_session)):
    origin = request.headers.get("origin")
    if origin:
        parsed = urlsplit(origin)
        if parsed.scheme not in {"http", "https"} or parsed.netloc != request.headers.get("host"):
            raise HTTPException(403, "Origin is not allowed")
    if request.headers.get("content-type", "").split(";")[0] != "application/json":
        return rpc_error(None, -32600, "Content-Type must be application/json", 415)
    raw = await request.body()
    if len(raw) > 1_000_000:
        return rpc_error(None, -32600, "MCP request exceeds one megabyte", 413)
    try:
        body = json.loads(raw, parse_constant=lambda value: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeDecodeError):
        return rpc_error(None, -32700, "Parse error")
    if not isinstance(body, dict) or body.get("jsonrpc") != "2.0":
        return rpc_error(None, -32600, "Expected one JSON-RPC 2.0 request")
    request_id, method, params = body.get("id"), body.get("method"), body.get("params", {})
    if (
        not isinstance(method, str)
        or not isinstance(params, dict)
        or ("id" in body and type(request_id) not in {str, int})
    ):
        return rpc_error(None, -32600, "Invalid request")
    failure = transport_error(request, body, params)
    if failure is not None:
        return failure
    if "id" not in body:
        if not method.startswith("notifications/"):
            return rpc_error(None, -32600, "Only notifications may omit id")
        return Response(status_code=202)
    if method == "initialize":
        requested = params.get("protocolVersion")
        return result(
            request_id,
            {
                "protocolVersion": requested if requested in VERSIONS else LEGACY,
                "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO,
                "instructions": INSTRUCTIONS,
            },
        )
    if method == "server/discover":
        return result(
            request_id,
            {
                "resultType": "complete",
                "supportedVersions": list(VERSIONS),
                "capabilities": {"tools": {}},
                "_meta": {"io.modelcontextprotocol/serverInfo": SERVER_INFO},
                "instructions": INSTRUCTIONS,
                "ttlMs": 60_000,
                "cacheScope": "private",
            },
        )
    if method == "ping":
        return result(request_id, {})
    admin = is_admin(request, session_id)
    if method == "tools/list":
        tools = TOOLS + ADMIN_TOOLS if admin else TOOLS
        run = request.app.state.store.snapshot()["runs"].get(session_id, {})
        if run.get("kind") == "tuning":
            from propadmin_core.workflow_tuning import READ_TOOLS

            tools = [t for t in TOOLS if t["name"] in READ_TOOLS]
        return result(request_id, {"tools": tools, "ttlMs": 60_000, "cacheScope": "private"})
    if method != "tools/call":
        return rpc_error(request_id, -32601, "Method not found", 404)
    name, args = params.get("name"), params.get("arguments", {})
    run = request.app.state.store.snapshot()["runs"].get(session_id, {"id": session_id})
    telemetry = request.app.state.telemetry
    catalogue = ADMIN_CATALOGUE if admin else CATALOGUE
    tool_name = name if isinstance(name, str) and name in catalogue else "unknown"
    with telemetry.for_run(
        run,
        f"execute_tool {tool_name}",
        {
            "name": name,
            "arguments": args,
            "request_id": request_id,
            "request_trace_id": current_ids().get("trace_id"),
        },
        attributes={"gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": tool_name},
    ) as outcome:
        response = await call_tool(request, session_id, request_id, name, args, admin)
        body = json.loads(response.body)
        result_body = body.get("result", {})
        outcome["result"] = result_body.get("structuredContent", body)
        if body.get("error") or result_body.get("isError"):
            outcome["error"] = body.get("error") or outcome["result"].get("error")
        return response


async def call_tool(request, session_id, request_id, name, args, admin=False):
    catalogue = ADMIN_CATALOGUE if admin else CATALOGUE
    if not isinstance(name, str) or name not in catalogue or not isinstance(args, dict):
        audit(
            request, session_id, name, args if isinstance(args, dict) else {}, "failed", "invalid"
        )
        return rpc_error(request_id, -32602, "Unknown tool or invalid arguments")
    try:
        validate(args, catalogue[name]["inputSchema"])
        run = request.app.state.store.snapshot()["runs"].get(session_id, {})
        if run.get("evaluation_id"):
            from .workflow_sandbox import execute_replay

            payload = execute_replay(request, name, args, run, execute)
        elif name in tools_admin.TOOLS:
            from .portal_policy import check_agent_control

            check_agent_control(request.app.state.store.snapshot(), session_id, name, args)
            payload = await tools_admin.call(request.app, name, args)
        else:
            payload = execute(request, name, args, session_id, admin)
    except HTTPException as exc:
        audit(request, session_id, name, args, "failed", "forbidden")
        payload = {"error": {"code": "forbidden", "detail": exc.detail}}
        return result(
            request_id,
            {
                "content": [{"type": "text", "text": json.dumps(payload)}],
                "structuredContent": payload,
                "isError": True,
            },
        )
    except (KeyError, ValueError, ProviderNotConfigured) as exc:
        code = "conflict" if isinstance(exc, ConflictError) else "invalid"
        if isinstance(exc, KeyError):
            code, message = "not_found", "Graph record not found"
        else:
            message = str(exc)
        if isinstance(exc, ProviderNotConfigured):
            code = "unavailable"
        audit(request, session_id, name, args, "failed", code)
        payload = {"error": {"code": code, "message": message}}
        return result(
            request_id,
            {
                "content": [{"type": "text", "text": json.dumps(payload)}],
                "structuredContent": payload,
                "isError": True,
            },
        )
    except Exception as exc:
        request.app.state.telemetry.emit(
            "tool.exception", {"type": type(exc).__name__, "message": str(exc)}, severity="ERROR"
        )
        audit(request, session_id, name, args, "failed", "internal")
        payload = {"error": {"code": "internal", "message": "Graph tool failed unexpectedly"}}
        return result(
            request_id,
            {
                "content": [{"type": "text", "text": json.dumps(payload)}],
                "structuredContent": payload,
                "isError": True,
            },
        )
    audit(request, session_id, name, args, "completed")
    return result(
        request_id,
        {
            "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}],
            "structuredContent": payload,
            "isError": False,
        },
    )


@router.api_route("/mcp", methods=["GET", "DELETE"], include_in_schema=False)
def unsupported_transport(session_id=Depends(require_session)):
    return Response(status_code=405, headers={"Allow": "POST"})


class TokenGrant(Input):
    session_id: str = Field(min_length=1, max_length=200, pattern=r"^[a-zA-Z0-9_:-]+$")
    reason: str = Field(default="Graph access", min_length=1, max_length=2000)
    lifetime_seconds: int = Field(default=3600, strict=True, ge=1, le=86400)
    scope: Literal["operations", "admin"] = "operations"


@router.post("/v1/mcp/tokens", dependencies=[Depends(require_admin)], status_code=201)
@router.post("/internal/mcp/tokens", dependencies=[Depends(require_internal)], status_code=201)
def grant_token(payload: TokenGrant, request: Request):
    cfg = request.app.state.settings

    def grant(state):
        grants = state.setdefault("mcp_sessions", {})
        if payload.session_id in grants:
            raise ConflictError("Session id already issued; use a new id to rotate tokens")
        grants[payload.session_id] = {
            "session_id": payload.session_id,
            "reason": payload.reason,
            "created_at": now(),
            "expires_at": int(time.time()) + payload.lifetime_seconds,
            "revoked": False,
            **({"scope": "admin"} if payload.scope == "admin" else {}),
        }
        publish(state, "mcp.granted", {"session_id": payload.session_id})

    request.app.state.store.mutate(grant)
    return {
        "token": issue_token(cfg, f"agent_run:{payload.session_id}", payload.lifetime_seconds),
        "session_id": payload.session_id,
        "expires_in": payload.lifetime_seconds,
        "endpoint": "/mcp",
    }


@router.get("/v1/mcp/tokens", dependencies=[Depends(require_admin)])
def list_grants(request: Request):
    return {"items": list(request.app.state.store.snapshot().get("mcp_sessions", {}).values())}


@router.delete("/v1/mcp/tokens/{session_id}", dependencies=[Depends(require_admin)])
def revoke_grant(session_id: str, request: Request):
    def revoke(state):
        grant = state.get("mcp_sessions", {})[session_id]
        grant.update(revoked=True, revoked_at=now())
        publish(state, "mcp.revoked", {"session_id": session_id})
        return {"session_id": session_id, "revoked": True}

    return request.app.state.store.mutate(revoke)
