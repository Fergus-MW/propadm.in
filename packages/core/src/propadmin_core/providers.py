"""Explicit external adapters. Missing configuration is never simulated success."""

import json
import os
import threading
from functools import lru_cache
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class ProviderNotConfigured(ValueError):
    pass


def http_json(url, payload=None, headers=None, timeout=45):
    request = Request(
        url,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except HTTPError as exc:
        # Provider bodies can contain secret request details; do not echo them.
        raise ValueError(f"External provider returned HTTP {exc.code}") from exc


class ClaudeProvider:
    def __init__(self):
        self.key = os.getenv("ANTHROPIC_API_KEY")
        self.model = os.getenv("PIPELINE_MODEL") or os.getenv("ANTHROPIC_PIPELINE_MODEL")
        if not self.key or not self.model:
            raise ProviderNotConfigured("Claude requires ANTHROPIC_API_KEY and PIPELINE_MODEL")

    def json(self, instruction, context):
        response = http_json(
            "https://api.anthropic.com/v1/messages",
            {
                "model": self.model,
                "max_tokens": 8192,
                "system": "Return the requested JSON object through submit_result. " + instruction,
                "messages": [{"role": "user", "content": json.dumps(context)}],
                "tools": [{
                    "name": "submit_result",
                    "description": "Return the complete JSON result specified in the instructions.",
                    "input_schema": {"type": "object", "additionalProperties": True},
                }],
                # Sonnet 5.5 rejects forced tool/any choices. Auto works across the
                # pipeline and browser models; validate the result below regardless.
                "tool_choice": {"type": "auto", "disable_parallel_tool_use": True},
            },
            {"x-api-key": self.key, "anthropic-version": "2023-06-01"},
        )
        if response.get("stop_reason") == "max_tokens":
            raise ValueError("Claude extraction exceeded its output token limit")
        results = [block.get("input") for block in response["content"]
                   if block.get("type") == "tool_use" and block.get("name") == "submit_result"]
        if len(results) != 1:
            raise ValueError("Claude did not return one structured result")
        result = results[0]
        if not isinstance(result, dict):
            raise ValueError("Claude response must be a JSON object")
        return result


class VertexEmbeddings:
    def __init__(self):
        self.project = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT_ID")
        self.location = os.getenv("VERTEX_LOCATION", "us-central1")
        self.model = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
        self.dimension = int(os.getenv("EMBEDDING_DIMENSIONS", "1536"))
        self._credentials = None
        self._credential_lock = threading.Lock()
        if not self.project:
            raise ProviderNotConfigured("Vertex embeddings require GOOGLE_CLOUD_PROJECT and ADC")

    @lru_cache(maxsize=512)
    def embed(self, text, query=False):
        try:
            import google.auth
            from google.auth.transport.requests import Request as AuthRequest
        except ImportError as exc:
            raise ProviderNotConfigured(
                "Install google-auth and requests for Vertex embeddings"
            ) from exc
        with self._credential_lock:
            if self._credentials is None:
                self._credentials, _ = google.auth.default(
                    scopes=["https://www.googleapis.com/auth/cloud-platform"]
                )
            credentials = self._credentials
            if not credentials.valid:
                credentials.refresh(AuthRequest())
            token = credentials.token
        url = (
            f"https://{self.location}-aiplatform.googleapis.com/v1/projects/{self.project}"
            f"/locations/{self.location}/publishers/google/models/{self.model}:predict"
        )
        response = http_json(
            url,
            {
                "instances": [
                    {
                        "content": text,
                        "task_type": "RETRIEVAL_QUERY" if query else "RETRIEVAL_DOCUMENT",
                    }
                ],
                "parameters": {"outputDimensionality": self.dimension},
            },
            {"Authorization": f"Bearer {token}"},
        )
        values = response["predictions"][0]["embeddings"]["values"]
        if len(values) != self.dimension:
            raise ValueError("Vertex embedding dimension does not match configured index")
        return values


class SurrealRepository:
    """HTTP repository for migrations and parameterised SurrealQL.

    Deliberately separate from the local Store: callers must select a production
    repository explicitly rather than assume JSON persistence is SurrealDB.
    """

    def __init__(self, url=None, namespace=None, database=None, token=None):
        self.url = url or os.getenv("SURREAL_URL")
        self.namespace = namespace or os.getenv("SURREAL_NAMESPACE", "propadmin")
        self.database = database or os.getenv("SURREAL_DATABASE", "main")
        self.token = token or os.getenv("SURREAL_TOKEN")
        if not self.url or not self.token:
            raise ProviderNotConfigured("SurrealDB requires SURREAL_URL and SURREAL_TOKEN")
        if not self.url.startswith(("https://", "http://localhost:", "http://127.0.0.1:")):
            raise ValueError("SurrealDB endpoint requires HTTPS outside localhost")

    def query(self, query, parameters=None):
        parameters = parameters or {}
        if any(not key.replace("_", "").isalnum() for key in parameters):
            raise ValueError("Invalid query parameter name")
        encoded = urlencode({key: json.dumps(value) for key, value in parameters.items()})
        request = Request(
            self.url.rstrip("/") + "/sql" + ("?" + encoded if encoded else ""),
            data=query.encode(),
            headers={
                "Accept": "application/json",
                "Content-Type": "text/plain",
                "Surreal-NS": self.namespace,
                "Surreal-DB": self.database,
                "Authorization": f"Bearer {self.token}",
            },
        )
        with urlopen(request, timeout=30) as response:
            statements = json.load(response)
        if any(statement.get("status") != "OK" for statement in statements):
            raise ValueError("SurrealDB rejected a query statement")
        return [statement["result"] for statement in statements]
