"""Ambiguous production submissions must recover the existing session."""

import httpx
import pytest

from eval.workflows.__main__ import evaluate


@pytest.mark.parametrize("saved_run", [True, False])
def test_submission_timeout_recovers_without_duplicate_run(monkeypatch, saved_run):
    monkeypatch.setattr("eval.workflows.__main__.time.sleep", lambda _: None)
    calls = []

    class Gateway:
        def request(self, method, path, body=None):
            calls.append((method, path))
            if path == "/v1/workflow-evaluations":
                return {"id": "workflow_evaluation:one"}
            if path.endswith("/run"):
                raise httpx.ReadTimeout("Response lost after submission")
            if path.startswith("/v1/entities/"):
                return {"fields": {"run_id": "agent_run:one"} if saved_run else {}}
            if path == "/v1/agent-runs/agent_run:one":
                return {"id": "agent_run:one", "status": "running"}
            if path.endswith("/sync"):
                if sum(p.endswith("/sync") for _, p in calls) == 1:
                    raise ValueError("HTTP 409: Concurrent updates")
                return {"id": "agent_run:one", "status": "done"}
            if path.endswith("/grade"):
                return {"fields": {"score": 80, "passed": True}}
            raise AssertionError(path)

    if saved_run:
        assert evaluate(Gateway(), {"id": "transition:one", "name": "1 → 2"}, 30)["fields"]["passed"]
    else:
        with pytest.raises(httpx.ReadTimeout):
            evaluate(Gateway(), {"id": "transition:one", "name": "1 → 2"}, 30)
    assert sum(p.endswith("/run") for _, p in calls) == 1
