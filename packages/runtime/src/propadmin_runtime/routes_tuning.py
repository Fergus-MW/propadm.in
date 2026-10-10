"""Admin controls and private uploads for autonomous workflow performance tuning."""

import asyncio
import logging

from fastapi import APIRouter, Depends, Request
from propadmin_core.store import now, publish
from propadmin_core.workflow_tuning import evaluation_record, sample_cases
from pydantic import Field, field_validator

from .auth import require_admin, require_internal
from .models import Input
from .services import call_service
from .workflow_tuner import create_job, job_record, tick

router = APIRouter(prefix="/v1/workflow-tuning", dependencies=[Depends(require_admin)])
internal = APIRouter(prefix="/internal/workflow-tuning", dependencies=[Depends(require_internal)])
logger = logging.getLogger(__name__)


class Start(Input):
    max_trials: int = Field(default=200, ge=10, le=10000)


class TestCase(Input):
    name: str = Field(min_length=1, max_length=200)
    initial_context: str = Field(default="", max_length=20000)
    steps: list[str] = Field(min_length=1, max_length=500)
    expected: str = Field(default="", max_length=30000)

    @field_validator("steps")
    @classmethod
    def valid_steps(cls, steps):
        if any(not s.strip() or len(s) > 30000 for s in steps) or sum(map(len, steps)) > 150000:
            raise ValueError(
                "Steps must be nonempty; case history may not exceed 150000 characters"
            )
        return steps


def present(job):
    return {
        key: value for key, value in job.items() if key not in {"uploaded", "lease", "lease_until"}
    }


@router.get("")
def overview(request: Request):
    state = request.app.state.store.snapshot()
    cases = sample_cases(state)
    jobs = sorted(
        (
            j
            for j in state["workflow_tuning_jobs"].values()
            if j.get("kind") in {"workflow_tuning", "workflow_test"}
        ),
        key=lambda j: j["created_at"],
        reverse=True,
    )
    return {
        "cases": len(cases),
        "transitions": sum(map(len, cases.values())),
        "items": [
            {
                key: j[key]
                for key in (
                    "id",
                    "name",
                    "kind",
                    "status",
                    "phase",
                    "created_at",
                    "streak",
                    "target",
                    "trials",
                    "max_trials",
                )
            }
            for j in jobs
        ],
    }


@router.post("/runs", status_code=201)
def start(payload: Start, request: Request):
    call_service(request.app.state.settings, "agent", "/internal/tuning/config", {})
    return present(create_job(request.app.state.store, payload.max_trials))


@router.post("/tests", status_code=201)
def test_case(payload: TestCase, request: Request):
    call_service(request.app.state.settings, "agent", "/internal/tuning/config", {})
    # Private runtime data only: never ingestion, documents, chunks, entities or embeddings.
    return present(create_job(request.app.state.store, uploaded=payload.model_dump()))


@router.get("/runs/{job_id}")
def get_job(job_id: str, request: Request):
    return present(job_record(request.app.state.store.snapshot(), job_id))


@router.post("/runs/{job_id}/stop")
def stop(job_id: str, request: Request):
    def save(state):
        job = job_record(state, job_id)
        if job["status"] == "running":
            job.update(status="stopped", updated_at=now())
            fields = (
                evaluation_record(state, job["evaluation_id"])["fields"]
                if job.get("evaluation_id")
                else {}
            )
            run_id = fields.get("run_id")
            if run_id:
                state.setdefault("mcp_sessions", {}).get(run_id, {})["revoked"] = True
            publish(state, "workflow_tuning.stopped", {"id": job_id})
        return job

    job = request.app.state.store.mutate(save)
    fields = (
        evaluation_record(request.app.state.store.snapshot(), job["evaluation_id"])["fields"]
        if job.get("evaluation_id")
        else {}
    )
    if fields.get("run_id"):
        run = request.app.state.store.snapshot()["runs"][fields["run_id"]]
        if run["status"] in {"queued", "running", "sleeping"}:
            try:
                call_service(
                    request.app.state.settings, "agent", f"/internal/runs/{run['id']}/cancel", {}
                )
            except Exception:
                logger.exception(
                    "Tuning stopped and MCP grant revoked; provider cancellation failed"
                )
    return present(job)


@internal.post("/tick")
def scheduled_tick(request: Request):
    return tick(request.app)


async def start_local_tuning_scheduler(app, poll_seconds=5):
    async def run():
        while True:
            await asyncio.sleep(poll_seconds)
            try:
                await asyncio.to_thread(tick, app)
            except Exception:
                logger.exception("Local workflow tuning tick failed")

    return asyncio.create_task(run(), name="propadmin-workflow-tuning")
