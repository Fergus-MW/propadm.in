"""Isolated Propadmin stacks per case behind one local server and one public tunnel.

Each case gets the production API app with its own in-memory graph (seeded skills and provider
directory, the case on ticket:case, placeholder contacts per party plus agency staff). Email and
voice providers are sandboxed: calls are recorded and return SIMULATED. Managed Agents sessions
reach each case's MCP gateway at <tunnel>/s<slot>/mcp.
"""

import collections
import copy
import json
import os
import re
import secrets
import shutil
import subprocess
import threading
import time
from pathlib import Path
from unittest.mock import patch

import httpx
import uvicorn
from propadmin_core import ProviderNotConfigured, Store, seed_demo
from propadmin_core.graph import add_edge
from propadmin_runtime import create_app
from propadmin_runtime.config import Settings

from services.agent.app import managed

ROOT = Path(__file__).resolve().parents[1]
AGENT_NAME = "Propadmin reality"
ENV_NAME = "propadmin-reality"
KEEP_TYPES = {"skill", "skill_version", "service_provider", "service_offering"}
SERVICE_MODULES = ("routes_email", "routes_voice", "routes_browser", "tools_agent", "routes_agent", "services")
STAFF_EMAIL = "maintenance-team@agency.sandbox.invalid"
_seed_lock, _seeded, APPS = threading.Lock(), None, {}
TUNNEL_LOG = collections.deque(maxlen=500)


def load_env():
    for name in (".env.local", ".env"):
        path = ROOT / name
        if path.exists():
            for line in path.read_text().splitlines():
                key, sep, value = line.partition("=")
                if sep and key.strip() and not key.startswith("#"):
                    os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def seeded_state():
    global _seeded
    with _seed_lock:
        if _seeded is None:
            with patch.dict(os.environ, {"EMBEDDING_PROVIDER": "local", "EXTRACTION_PROVIDER": "local"}):
                store = Store()
                seed_demo(store)
                _seeded = store.snapshot()
        return _seeded


def sandboxed_call(settings, name, path, payload=None, **_):
    app = APPS.get(id(settings))
    attempts = app.state.provider_attempts if app else []
    attempts.append({"service": name, "path": path, "payload": payload})
    n = len(attempts)
    if name == "email" and path in {"/internal/send", "/internal/reply"}:
        return {"email_id": f"email:sandbox-{n}", "status": "simulated", "delivered": False, "mode": "SIMULATED",
                "note": "Sandboxed email provider: recorded, not delivered."}
    if name == "voice" and path == "/internal/calls":
        return {"call_id": f"call:sandbox-{n}", "status": "simulated", "mode": "SIMULATED",
                "note": "Sandboxed voice provider: no call was placed and no transcript will arrive."}
    if name == "browser" and path.endswith("/close"):
        return {"status": "closed"}
    raise ProviderNotConfigured(f"Provider unavailable in this run: {name} {path}; nothing was delivered")


class MCPTrace:
    """Record every MCP tools/call with its response."""

    def __init__(self, app, trace):
        self.app, self.trace = app, trace

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"] != "/mcp":
            return await self.app(scope, receive, send)
        request, response = bytearray(), bytearray()

        async def recv():
            message = await receive()
            request.extend(message.get("body", b""))
            return message

        async def emit(message):
            response.extend(message.get("body", b""))
            await send(message)

        try:
            await self.app(scope, recv, emit)
        finally:
            try:
                payload, result = json.loads(request), json.loads(response)
            except (ValueError, UnicodeDecodeError):
                payload, result = {}, {"unparsed": bytes(response).decode(errors="replace")[:2000]}
            if payload.get("method") == "tools/call":
                self.trace.append({"at": time.time(), "request": payload["params"], "response": result})


def contacts():
    def person(key, role, i):
        return {"id": f"person:case-{key}", "type": "person", "name": f"{role.title()} (named in the case file)",
                "fields": {"roles": [role], "emails": [f"{key}@case.sandbox.invalid"], "phones": [f"+4420794601{i:02d}"]}}
    return [person("tenant", "tenant", 1), person("landlord", "landlord", 2),
            {"id": "company:case-contractor", "type": "company", "name": "Contractor (named in the case file)",
             "fields": {"type": "contractor", "emails": ["contractor@case.sandbox.invalid"],
                        "phones": ["+442079460103"]}},
            {"id": "person:agency-staff", "type": "person", "name": "Agency maintenance team",
             "fields": {"roles": ["staff"], "emails": [STAFF_EMAIL], "phones": ["+442079460100"]}}]


def build(case, mcp_url, system):
    seeded = seeded_state()
    store = Store()

    def init(state):
        kept = {k: v for k, v in seeded["entities"].items() if v["type"] in KEEP_TYPES}
        state["entities"].update(copy.deepcopy(kept))
        state["edges"].update({k: copy.deepcopy(v) for k, v in seeded["edges"].items()
                               if v["source"] in kept and v["target"] in kept})
        state["embeddings"].update({k: copy.deepcopy(v) for k, v in seeded["embeddings"].items()
                                    if v.get("owner") in kept})
        state["skills"] = copy.deepcopy(seeded["skills"])

    store.mutate(init)
    settings = Settings(mode="cloud", admin_password=secrets.token_urlsafe(32),
                        token_secret=secrets.token_urlsafe(32), internal_token=secrets.token_urlsafe(32))
    app = create_app("api", store=store, settings=settings, seed=False)
    app.include_router(managed.router)
    app.state.case_trace, app.state.provider_attempts = [], []
    app.state.case_mcp_url, app.state.case_system = mcp_url, system
    app.add_middleware(MCPTrace, trace=app.state.case_trace)
    app.state.graph.create_entity({"id": "ticket:case", "type": "ticket", "name": case["title"][:200],
                                   "description": case["text"], "fields": {"status": "reported"}},
                                  reason="Case file received")
    for entity in contacts():
        app.state.graph.create_entity(entity, reason="Sandbox contact for a party in the case file")
    address = re.search(r"\*\*Property:\*\*\s*(.+)", case["text"])
    postcode = re.search(r"[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\s*$", address.group(1).strip()) if address else None
    if address and postcode:  # only when the case file states the address; never invented
        line = address.group(1).strip()
        app.state.graph.create_entity({"id": "property:case", "type": "property", "name": line[:200], "fields": {
            "ref": "case", "address_line1": line.split(",")[0].strip(), "address_text": line,
            "postcode": postcode.group(0).strip()}}, reason="Property stated in the case file")

    def link(state):
        add_edge(state, "ticket:case", "person:case-tenant", "reported_by")
        if "property:case" in state["entities"]:
            add_edge(state, "ticket:case", "property:case", "for")

    store.mutate(link)
    APPS[id(settings)] = app
    return app


# ------------------------------------------------------------------ serving

class Slots:
    """ASGI dispatcher: /s<i>/<path> goes to the case app currently in slot i."""

    def __init__(self, count):
        self.apps = [None] * count
        self.nonce = secrets.token_hex(8)

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            while True:
                message = await receive()
                done = message["type"] == "lifespan.shutdown"
                await send({"type": "lifespan.shutdown.complete" if done else "lifespan.startup.complete"})
                if done:
                    return
        if scope.get("path") == "/_probe":
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": self.nonce.encode()})
            return
        match = re.match(r"^/s(\d+)(/.*)$", scope.get("path", ""))
        app = self.apps[int(match.group(1))] if match and int(match.group(1)) < len(self.apps) else None
        if app is None:
            await send({"type": "http.response.start", "status": 404, "headers": []})
            await send({"type": "http.response.body", "body": b"no case in this slot"})
            return
        await app(dict(scope, path=match.group(2), raw_path=match.group(2).encode()), receive, send)


def serve(router, port):
    server = uvicorn.Server(uvicorn.Config(router, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    deadline = time.monotonic() + 10
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.05)
    if not server.started:
        raise RuntimeError("Local case server failed to start")
    return server


def tunnel(port):
    """Public HTTPS URL for the local server: a Cloudflare quick tunnel, else ngrok."""
    if shutil.which("cloudflared"):
        return cloudflare_tunnel(port)
    return ngrok_tunnel(port)


def cloudflare_tunnel(port):
    process = subprocess.Popen(["cloudflared", "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{port}"],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        line = process.stdout.readline()
        if not line:
            break
        TUNNEL_LOG.append(line)
        found = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
        if found:
            threading.Thread(target=lambda: [TUNNEL_LOG.append(x) for x in process.stdout], daemon=True).start()
            return process, found.group(0)
    process.kill()
    raise RuntimeError("cloudflared did not start a quick tunnel")


def ngrok_tunnel(port):
    process = subprocess.Popen(["ngrok", "http", str(port), "--log", "stdout", "--log-format", "json"],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        line = process.stdout.readline()
        if not line:
            break
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("url", "").startswith("https://"):
            # ngrok logs every request; an undrained pipe fills and freezes the tunnel.
            threading.Thread(target=lambda: [TUNNEL_LOG.append(x) for x in process.stdout], daemon=True).start()
            return process, event["url"]
        if event.get("lvl") in {"eror", "crit"}:
            break
    process.kill()
    raise RuntimeError("ngrok did not start a public tunnel")


# ------------------------------------------------------------------ Managed Agents

_case = threading.local()
_production_ma = managed.ma


def ma_for_case(method, path, payload=None, params=None):
    """Production managed.ma, pointing this thread's session and credential at its case."""
    ctx = getattr(_case, "value", None)
    if ctx and method == "POST" and payload:
        if path == "/sessions":
            agent = payload["agent"] if isinstance(payload["agent"], str) else payload["agent"]["id"]
            payload = {**payload, "agent": {"type": "agent_with_overrides", "id": agent, "system": ctx["system"],
                                            "mcp_servers": [{"type": "url", "name": "propadmin", "url": ctx["url"]}]}}
        elif path.endswith("/credentials"):
            payload = {**payload, "auth": {**payload["auth"], "mcp_server_url": ctx["url"]}}
    return _production_ma(method, path, payload, params)


def public_ip(host):
    """Resolve through Cloudflare DNS-over-HTTPS: local resolvers often miss fresh tunnel hostnames."""
    response = httpx.get("https://cloudflare-dns.com/dns-query", params={"name": host, "type": "A"},
                         headers={"accept": "application/dns-json"}, timeout=10)
    answers = [a["data"] for a in response.json().get("Answer", []) if a.get("type") == 1]
    return answers[0] if answers else None


def tunnel_ok(base_url, router):
    """The public URL reaches this server: /_probe returns this router's nonce."""
    host = base_url.split("//", 1)[1]
    try:
        ip = public_ip(host)
        if not ip:
            return False
        with httpx.Client(timeout=10) as client:
            response = client.send(client.build_request("GET", f"https://{ip}/_probe", headers={"Host": host},
                                                        extensions={"sni_hostname": host}))
    except (httpx.HTTPError, ValueError):
        return False
    return response.status_code == 200 and response.text == router.nonce


def mcp_failed(session_id):
    """True when the session reported it could not reach the MCP server."""
    events = _production_ma("GET", f"/sessions/{session_id}/events", params={"limit": 100, "order": "desc"})
    return any(e.get("type") == "session.error" and "mcp" in json.dumps(e.get("error", {})).lower()
               for e in events.get("data", []))


def find(path, name):
    page = None
    while True:
        body = managed.ma("GET", path, params={"limit": 100, **({"page": page} if page else {})})
        for item in body.get("data", []):
            if item.get("name") == name and not item.get("archived_at"):
                return item
        page = body.get("next_page")
        if not page:
            return None


def ensure_agent(url):
    """A dedicated agent and environment with the production definition."""
    from infra.scripts.managed_agent import MODEL, SYSTEM
    env = find("/environments", ENV_NAME) or managed.ma("POST", "/environments", {
        "name": ENV_NAME, "description": "Propadmin case runner sandbox.",
        "config": {"type": "cloud", "networking": {"type": "limited", "allow_mcp_servers": True,
                                                    "allow_package_managers": True}}})
    agent = find("/agents", AGENT_NAME) or managed.ma("POST", "/agents", {
        "name": AGENT_NAME, "model": MODEL, "system": SYSTEM,
        "description": "Production Propadmin definition used by the case runner; MCP URL set per session.",
        "mcp_servers": [{"type": "url", "name": "propadmin", "url": url}],
        "tools": [
            {"type": "agent_toolset_20260401",
             "default_config": {"enabled": True, "permission_policy": {"type": "always_allow"}},
             "configs": [{"name": "web_fetch", "enabled": False}, {"name": "web_search", "enabled": False}]},
            {"type": "mcp_toolset", "mcp_server_name": "propadmin",
             "default_config": {"permission_policy": {"type": "always_allow"}}}],
        "metadata": {"app": "propadmin", "purpose": "case-runner"}})
    return agent, env
