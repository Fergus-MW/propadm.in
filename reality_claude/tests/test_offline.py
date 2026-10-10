"""Offline checks for the case runner: intake, the isolated stack and answer rendering."""

import asyncio
import json
from pathlib import Path

import httpx
import pytest

from reality_claude import report, stack
from reality_claude.intake import discover, read_case
from services.agent.app import managed

CASES = Path(__file__).resolve().parents[2] / "Property Management"


def test_discover_numbers_answers_from_folder_names(tmp_path):
    for name in ("case-3", "10", "alpha"):
        (tmp_path / name).mkdir()
        (tmp_path / name / "index.md").write_text(f"# {name}\n")
    ids = {c["path"].name: c["answer_id"] for c in discover(tmp_path)}
    assert ids["10"] == "10" and ids["case-3"] == "3"
    assert len(set(ids.values())) == 3


def test_read_case_orders_files_reads_pdfs_and_can_hide_outcome():
    case = read_case({"answer_id": "5", "path": CASES / "005"}, hide_outcome=True)
    names = [f["file"] for f in case["files"]]
    assert names[:2] == ["index.md", "history.md"]
    assert any(f["file"].endswith(".pdf") and f["status"] == "read" for f in case["files"])
    assert "## Outcome" not in case["text"] and "## Overview" not in case["text"]
    assert case["events"] > 10 and case["case_time"]
    full = read_case({"answer_id": "5", "path": CASES / "005"})
    assert "## Outcome" in full["text"]


def test_unreadable_attachment_is_listed_not_fatal(tmp_path):
    (tmp_path / "1").mkdir()
    (tmp_path / "1/history.md").write_text("event text")
    (tmp_path / "1/photo.jpg").write_bytes(b"\xff\xd8")
    (tmp_path / "1/broken.pdf").write_bytes(b"not a pdf")
    case = read_case(discover(tmp_path)[0])
    status = {f["file"]: f["status"] for f in case["files"]}
    assert status["history.md"] == "read"
    assert status["photo.jpg"].startswith("unreadable") and status["broken.pdf"].startswith("unreadable")


def mcp_call(app, name, arguments):
    router = stack.Slots(1)
    router.apps[0] = app
    token = managed.grant(app, "agent_run:test-runner")
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json, text/event-stream",
               "MCP-Protocol-Version": "2026-07-28", "Mcp-Method": "tools/call", "Mcp-Name": name}
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
        "name": name, "arguments": arguments, "_meta": {"io.modelcontextprotocol/protocolVersion": "2026-07-28"}}}

    async def go():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=router), base_url="http://h") as client:
            return await client.post("/s0/mcp", json=body, headers=headers)

    return asyncio.run(go())


@pytest.fixture(scope="module")
def app():
    case = read_case({"answer_id": "13", "path": CASES / "013"}, hide_outcome=True)
    return stack.build(case, "https://example.invalid/s0/mcp", "system")


def test_case_file_skills_and_staff_are_reachable_over_mcp(app):
    ticket = mcp_call(app, "get_entity", {"id": "ticket:case"}).json()["result"]["structuredContent"]
    assert "===== history.md =====" in ticket["description"]
    skill = mcp_call(app, "get_skill", {"skill": "escalation-and-handover"}).json()["result"]["structuredContent"]
    assert "Hand over when" in skill["content"]
    staff = mcp_call(app, "get_entity", {"id": "person:agency-staff"}).json()["result"]["structuredContent"]
    assert staff["fields"]["emails"] == [stack.STAFF_EMAIL]


def test_report_renders_actions_staff_failures_and_simulated_labels(tmp_path):
    def call(name, arguments, result):
        return {"request": {"name": name, "arguments": arguments}, "response": {"result": result}}
    record = {
        "answer_id": "7", "title": "Gas smell", "mode": "live", "execution": "sleeping", "finished": "now",
        "files": [{"file": "history.md", "status": "read", "bytes": 10}], "events": 3, "case_time": "x",
        "decision": "Decision: safety steps given; staff alerted.",
        "calls": [
            call("get_skill", {"skill": "emergency-response"}, {"structuredContent": {"content": "..."}}),
            call("send_email", {"to": [stack.STAFF_EMAIL], "subject": "STAFF DECISION NEEDED: gas", "body": "b"},
                 {"structuredContent": {"mode": "SIMULATED", "note": "not delivered"}}),
            call("update_entity", {"id": "ticket:case", "fields": {"tags": ["needs-staff"]}}, {"structuredContent": {}}),
            call("place_call", {"entity_id": "person:case-tenant", "objective": "safety"},
                 {"isError": True, "content": [{"type": "text", "text": "no phone"}]}),
        ],
        "plan": {"goal": "g", "steps": [{"title": "Safety", "status": "done", "evidence": "sent"}]},
        "ticket": {"status": "triaged", "tags": ["needs-staff"]}, "messages": ["Decision: ..."]}
    report.write(record, tmp_path)
    answer = (tmp_path / "7/ANSWER.md").read_text()
    assert "Emailed agency staff" in answer and "Tagged ticket:case needs-staff" in answer
    assert "| SIMULATED" in answer and "place_call: no phone" in answer
    reasoning = (tmp_path / "7/REASONING.md").read_text()
    assert "emergency-response" in reasoning and "[done] Safety" in reasoning
    assert json.loads((tmp_path / "7/trace.json").read_text())["answer_id"] == "7"
    index = report.index_md([{"answer_id": "7", "title": "Gas smell", "execution": "sleeping", "mode": "live",
                              "staff": True, "actions": 3, "failures": 1, "seconds": 9}])
    assert "[7](7/ANSWER.md)" in index


def test_probe_answers_from_the_router_even_when_slots_are_busy(app):
    router = stack.Slots(1)
    router.apps[0] = app

    async def go():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=router), base_url="http://h") as client:
            return await client.get("/_probe"), await client.get("/s0/anything")

    probe, busy = asyncio.run(go())
    assert probe.status_code == 200 and probe.text == router.nonce
    assert b"no case in this slot" not in busy.content
