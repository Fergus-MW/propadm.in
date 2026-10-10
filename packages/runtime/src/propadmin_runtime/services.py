"""Authenticated service-to-service calls. A missing URL is an explicit 503, never a fake success."""

import os

import httpx
from propadmin_core import ProviderNotConfigured

from .observability import current_ids, propagation_headers


def service_url(name):
    url = os.getenv(f"{name.upper()}_SERVICE_URL")
    if not url:
        raise ProviderNotConfigured(
            f"{name} service is not configured ({name.upper()}_SERVICE_URL)"
        )
    return url.rstrip("/")


def call_service(settings, name, path, payload=None, method="POST", timeout=60):
    response = httpx.request(
        method,
        service_url(name) + path,
        json=payload,
        timeout=timeout,
        headers={"Authorization": f"Bearer {settings.internal_token}", **propagation_headers()},
    )
    if response.status_code == 503:
        raise ProviderNotConfigured(
            response.json().get("detail", f"{name} provider not configured")
        )
    if response.status_code >= 400:
        raise ValueError(f"{name} service returned HTTP {response.status_code}")
    return response.json()


def record_action(
    store, run_id, tool, arguments, result=None, reason="", entity_id=None, error=None
):
    """Append one audited agent action (F13: no approval step, every action logged)."""
    from propadmin_core import publish
    from propadmin_core.store import identifier, now

    def write(state):
        action = {
            "id": identifier("action"),
            "session": run_id,
            "actor": f"agent_run:{run_id}",
            "tool": tool,
            "arguments": arguments,
            "result": result,
            "error": error,
            "reason": reason,
            "entity_id": entity_id,
            "created_at": now(),
            "span_id": current_ids().get("span_id"),
        }
        state["actions"][action["id"]] = action
        publish(state, "action.recorded", {"id": action["id"], "session": run_id, "tool": tool})
        return action

    return store.mutate(write)
