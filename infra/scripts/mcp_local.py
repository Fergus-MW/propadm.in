"""Register the running local API's admin-scope /mcp gateway with Claude Code."""

import json
import os
import subprocess
import time
from urllib.request import Request, urlopen

API = os.getenv("API_URL", "http://127.0.0.1:8000")
PASSWORD = os.getenv("ADMIN_PASSWORD", "propadmin-local")


def post(path, payload, token=None):
    headers = {"content-type": "application/json"}
    if token:
        headers["authorization"] = f"Bearer {token}"
    request = Request(API + path, json.dumps(payload).encode(), headers)
    with urlopen(request, timeout=10) as response:
        return json.load(response)


def main():
    admin = post("/v1/auth/login", {"password": PASSWORD})["token"]
    grant = post(
        "/v1/mcp/tokens",
        {
            "session_id": f"claude-code-{int(time.time())}",
            "reason": "Local Claude Code admin MCP access",
            "lifetime_seconds": 86400,
            "scope": "admin",
        },
        admin,
    )
    subprocess.run(["claude", "mcp", "remove", "propadmin", "-s", "local"], capture_output=True)
    subprocess.run(
        ["claude", "mcp", "add", "--transport", "http", "-s", "local", "propadmin",
         f"{API}/mcp", "--header", f"Authorization: Bearer {grant['token']}"],
        check=True,
    )
    print(f"Registered propadmin MCP ({API}/mcp, admin scope, expires in 24h). "
          "Restart Claude Code to load it; rerun `make mcp` after expiry.")


if __name__ == "__main__":
    main()
