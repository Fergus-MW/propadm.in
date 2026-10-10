"""Explicit local mode; public settings never expose provider secrets."""

import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    mode: str = field(default_factory=lambda: os.getenv("PROPADMIN_MODE", "local"))
    data_path: str = field(
        default_factory=lambda: os.getenv("PROPADMIN_DATA_PATH", ".data/state.json")
    )
    admin_password: str = field(default_factory=lambda: os.getenv("ADMIN_PASSWORD", ""))
    token_secret: str = field(default_factory=lambda: os.getenv("TOKEN_SECRET", ""))
    internal_token: str = field(default_factory=lambda: os.getenv("INTERNAL_SERVICE_TOKEN", ""))

    def __post_init__(self):
        if self.mode not in {"local", "cloud"}:
            raise ValueError("PROPADMIN_MODE must be local or cloud")
        if self.mode == "local":
            self.admin_password = self.admin_password or "propadmin-local"
            self.token_secret = self.token_secret or "propadmin-local-signing-key-development-only"
            self.internal_token = self.internal_token or "propadmin-local-internal-development-only"
        elif not all((self.admin_password, self.token_secret, self.internal_token)):
            raise ValueError(
                "Cloud mode requires ADMIN_PASSWORD, TOKEN_SECRET and INTERNAL_SERVICE_TOKEN"
            )

    def public(self):
        embedding_mode = os.getenv("EMBEDDING_PROVIDER", "local")
        pipeline_mode = os.getenv("EXTRACTION_PROVIDER", "local")
        return {
            "mode": self.mode,
            "database": "GCS JSON object (generation CAS)"
            if self.data_path.startswith("gs://")
            else "local JSON"
            if self.mode == "local"
            else "durable repository",
            "built_services": [
                "admin-panel",
                "api",
                "ingestion",
                "rules",
                "agent",
                "voice",
                "email",
                "browser",
            ],
            "mcp_endpoint": "/mcp",
            "providers": {
                "extraction": {
                    "provider": pipeline_mode,
                    "model": os.getenv("PIPELINE_MODEL") or "local-structured-exact-v1",
                    "configured": bool(
                        os.getenv("ANTHROPIC_API_KEY") and os.getenv("PIPELINE_MODEL")
                    ),
                },
                "embeddings": {
                    "provider": embedding_mode,
                    "model": "local-deterministic-hash-v1"
                    if embedding_mode == "local"
                    else os.getenv("EMBEDDING_MODEL", "gemini-embedding-001"),
                    "dimensions": 256
                    if embedding_mode == "local"
                    else int(os.getenv("EMBEDDING_DIMENSIONS", "1536")),
                    "offline": embedding_mode == "local",
                },
                "vertex_embeddings": {
                    "configured": bool(
                        os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT_ID")
                    ),
                    "active": embedding_mode == "vertex",
                },
                "managed_agents": {
                    "configured": bool(
                        os.getenv("ANTHROPIC_API_KEY") and os.getenv("MANAGED_AGENT_ID")
                    )
                },
                "elevenlabs": {
                    "configured": bool(
                        os.getenv("ELEVENLABS_API_KEY") and os.getenv("ELEVENLABS_AGENT_ID")
                    )
                },
                "agentmail": {"configured": bool(os.getenv("AGENTMAIL_API_KEY"))},
                "browserbase": {
                    "configured": bool(
                        os.getenv("BROWSERBASE_API_KEY") and os.getenv("BROWSERBASE_PROJECT_ID")
                    )
                },
                "services": {
                    name: bool(os.getenv(f"{name.upper()}_SERVICE_URL"))
                    for name in ("rules", "agent", "voice", "email", "browser")
                },
                "surrealdb": {
                    "configured": bool(os.getenv("SURREAL_URL")),
                    "runtime_connected": False,
                },
            },
        }
