"""Reconcile ElevenLabs call termination without replacing existing server tools.

ELEVENLABS_API_KEY and ELEVENLABS_AGENT_ID must be configured in the environment.
Credentials are never printed. Run after changing the voice provider setup.
"""

import os

import httpx

ENDING = """Call termination:
- Once the objective is complete, say one short goodbye and use end_call immediately.
- If you reach voicemail, leave one brief message identifying Properly and the call's
  purpose, then use end_call. Do not ask voicemail questions or repeat your goodbye.
- Respect any shorter time limit in the objective. For a production test, take no
  property actions, book no visits and contact nobody else.
"""


def configuration(current):
    agent = current["conversation_config"]["agent"]
    prompt = agent["prompt"]
    text = prompt["prompt"].replace("Propadmin assistant", "Properly assistant")
    if "Call termination:" not in text:
        text += "\n\n" + ENDING
    tools = {**(prompt.get("built_in_tools") or {}), "end_call": {
        "type": "system", "name": "end_call",
        "description": "End immediately after one goodbye, or after leaving a voicemail message.",
        "params": {"system_tool_type": "end_call"},
    }}
    payload = {"conversation_config": {
        "agent": {
            "first_message": agent.get("first_message", "").replace("Propadmin", "Properly"),
            "prompt": {"prompt": text, "built_in_tools": tools},
        },
        "turn": {"silence_end_call_timeout": 25},
    }}
    overrides = current.get("platform_settings", {}).get("workspace_overrides", {})
    webhooks = overrides.get("webhooks")
    if webhooks:
        # ElevenLabs replaces workspace_overrides as a unit, rather than merging
        # its children. Preserve initiation authentication and export settings.
        payload["platform_settings"] = {"workspace_overrides": {
            **overrides,
            "webhooks": {**webhooks,
                "events": list(dict.fromkeys([*webhooks.get("events", []), "call_initiation_failure"])),
            },
        }}
    return payload


def main():
    agent_id = os.environ["ELEVENLABS_AGENT_ID"]
    with httpx.Client(base_url="https://api.elevenlabs.io", timeout=45,
                      headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]}) as client:
        path = f"/v1/convai/agents/{agent_id}"
        before = client.get(path)
        before.raise_for_status()
        response = client.patch(path, json=configuration(before.json()))
        if response.status_code >= 400:
            raise RuntimeError(f"ElevenLabs configuration returned HTTP {response.status_code}")
        after = client.get(path)
        after.raise_for_status()
        config = after.json()["conversation_config"]
        assert config["agent"]["prompt"]["built_in_tools"]["end_call"]
        assert config["agent"]["prompt"].get("tool_ids") == before.json()["conversation_config"]["agent"]["prompt"].get("tool_ids")
        assert config["turn"]["silence_end_call_timeout"] == 25
        assert "Propadmin" not in config["agent"].get("first_message", "")
        webhooks = after.json().get("platform_settings", {}).get("workspace_overrides", {}).get("webhooks")
        if webhooks:
            assert "call_initiation_failure" in webhooks["events"]
        assert after.json().get("platform_settings", {}).get("workspace_overrides", {}).get(
            "conversation_initiation_client_data_webhook"
        ) == before.json().get("platform_settings", {}).get("workspace_overrides", {}).get(
            "conversation_initiation_client_data_webhook"
        )
        print("Voice termination, Properly greeting and failure subscription verified; server tools preserved")


if __name__ == "__main__":
    main()
