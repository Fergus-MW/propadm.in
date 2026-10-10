"""Administrative tooling always reads/writes the graph through the single API MCP."""

import os
import uuid
from urllib.parse import urlsplit

import httpx


class Gateway:
    def __init__(self, url, token=None):
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.hostname in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("Workflow corpus tooling requires an explicit production HTTPS API URL")
        self.http = httpx.Client(base_url=url.rstrip("/"), timeout=300)
        token = token or os.getenv("PROPADMIN_ADMIN_TOKEN")
        if not token:
            password = os.getenv("PROPADMIN_ADMIN_PASSWORD")
            if not password:
                raise ValueError("Set PROPADMIN_ADMIN_TOKEN or PROPADMIN_ADMIN_PASSWORD")
            response = self.http.post("/v1/auth/login", json={"password": password})
            response.raise_for_status()
            token = response.json()["token"]
        self.admin_headers = {"Authorization": f"Bearer {token}"}
        self.session_id = "workflow-corpus-" + uuid.uuid4().hex[:16]
        response = self.http.post("/v1/mcp/tokens", headers=self.admin_headers, json={
            "session_id": self.session_id, "scope": "admin", "lifetime_seconds": 86400,
            "reason": "Authorized production historical corpus ingestion/evaluation",
        })
        response.raise_for_status()
        self.headers = {"Authorization": f"Bearer {response.json()['token']}",
                        "Accept": "application/json, text/event-stream",
                        "MCP-Protocol-Version": "2025-11-25"}
        settings = self.request("GET", "/v1/settings")
        if settings["mode"] != "cloud":
            self.close()
            raise ValueError("Refusing changes: target API is not in production cloud mode")

    def request(self, method, path, body=None, query=None):
        response = self.http.post("/mcp", headers=self.headers, json={
            "jsonrpc": "2.0", "id": uuid.uuid4().hex, "method": "tools/call", "params": {
                "name": "admin_api", "arguments": {
                    "method": method, "path": path,
                    **({"body": body} if body is not None else {}),
                    **({"query": query} if query is not None else {}),
                    **({"reason": "Historical corpus ingestion/evaluation requested by administrator"}
                       if method != "GET" else {}),
                },
            },
        })
        response.raise_for_status()
        result = response.json()
        if "error" in result:
            raise ValueError(str(result["error"]))
        result = result["result"]
        if result.get("isError"):
            raise ValueError(result["structuredContent"]["error"]["message"])
        return result["structuredContent"]["data"]

    def close(self):
        try:
            self.http.delete(f"/v1/mcp/tokens/{self.session_id}", headers=self.admin_headers).raise_for_status()
        finally:
            self.http.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
