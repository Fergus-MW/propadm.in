"""Durable hill climbing: predict, grade, propose, validate, regress, publish."""

import copy
import json
import random
import time

from propadmin_core.graph import add_edge, create_in_state, record_change, update_in_state
from propadmin_core.store import ConflictError, identifier, initial_state, now, publish
from propadmin_core.workflow_corpus import RUBRIC_VERSION
from propadmin_core.workflow_judge import grade
from propadmin_core.workflow_tuning import (
    PREDICT_INSTRUCTIONS,
    REVISION_INSTRUCTIONS,
    evaluation_record,
    prediction,
    prepare_sample,
    sample_cases,
    skill_candidate,
)

from .routes_agent import publish_version
from .services import call_service

TERMINAL = {"completed", "stopped", "failed", "exhausted"}


def job_record(state, key):
    job = state["workflow_tuning_jobs"][key]
    if job.get("kind") not in {"workflow_tuning", "workflow_test"}:
        raise ValueError("Expected performance tuning job")
    return job


def create_job(store, max_trials=200, uploaded=None):
    key = identifier("workflow_test" if uploaded else "workflow_tuning")

    def write(state):
        if not uploaded:
            if any(
                j.get("kind") == "workflow_tuning" and j["status"] == "running"
                for j in state["workflow_tuning_jobs"].values()
            ):
                raise ConflictError("A tuning loop is already running")
            if sum(map(len, sample_cases(state).values())) < 10:
                raise ValueError("Tuning needs at least 10 eligible corpus transitions")
        job = {
            "id": key,
            "kind": "workflow_test" if uploaded else "workflow_tuning",
            "name": uploaded["name"] if uploaded else "Workflow tuning",
            "status": "running",
            "phase": "sample",
            "streak": 0,
            "target": 10,
            "trials": 0,
            "max_trials": max_trials,
            "history": [],
            "successful": [],
            "changes": [],
            "rejected": [],
            "evaluation_id": None,
            "created_at": now(),
            "updated_at": now(),
            "lease_until": 0,
            "uploaded": copy.deepcopy(uploaded),
        }
        state["workflow_tuning_jobs"][key] = job
        publish(state, "workflow_tuning.started", {"id": key})
        return job

    return store.mutate(write)


def new_evaluation(store, key, sample, mode="prediction", context=None):
    evaluation_id = identifier("workflow_evaluation")

    def write(state):
        job = job_record(state, key)
        if job["status"] != "running":
            return None
        catalogue = [
            {
                "slug": s["slug"],
                "name": s["name"],
                "description": s["description"],
                "current_version": s["current_version"],
            }
            for s in sample["state"]["skills"].values()
        ]
        payload = {
            "id": evaluation_id,
            "type": "workflow_evaluation",
            "name": f"Tuning {job['name']} · {job['phase']}",
            "fields": {
                "tuning_mode": mode,
                "transition_id": sample["transition_id"],
                "case_id": sample["case_id"],
                "status": "prepared",
                "context": context
                or PREDICT_INSTRUCTIONS
                + "\n\nAvailable workflow skills:\n"
                + json.dumps(catalogue, ensure_ascii=False)
                + "\n\n"
                + sample["context"],
                "context_hash": sample["context_hash"],
                "expected": sample["expected"],
                "skill_versions": sample["skill_versions"],
                "rubric_version": RUBRIC_VERSION,
            },
        }
        if job["uploaded"]:
            entity = {**payload, "version": 1, "created_at": now(), "updated_at": now()}
            state["workflow_private_evaluations"][evaluation_id] = entity
        else:
            entity = create_in_state(
                state, payload, "tuning", "Prepare case-isolated performance test"
            )
        # Runtime job state (including answer keys) is never part of the MCP sandbox.
        # Persist a mask and frozen skills rather than duplicating the entire corpus
        # on every trial. MCP reconstructs the permitted graph view on each read.
        sandbox = initial_state()
        sandbox["tuning_view"] = {
            "case_id": None if job["uploaded"] else sample["case_id"],
            "skills": sample["state"]["skills"],
            "skill_entities": {
                k: e
                for k, e in sample["state"]["entities"].items()
                if e["type"] in {"skill", "skill_version"}
            },
        }
        state["workflow_sandboxes"][evaluation_id] = sandbox
        job["evaluation_id"] = evaluation_id
        job["updated_at"] = now()
        return entity

    return store.mutate(write)


def launch(app, evaluation_id):
    evaluation = evaluation_record(app.state.store.snapshot(), evaluation_id)
    if evaluation["fields"]["status"] == "prepared":
        call_service(
            app.state.settings,
            "agent",
            "/internal/runs",
            {
                "goal": "Improve workflow skills"
                if evaluation["fields"]["tuning_mode"] == "revision"
                else "Predict the next workflow step",
                "subjects": [],
                "evaluation_id": evaluation_id,
            },
        )


def sample_job(app, job):
    state = app.state.store.snapshot()
    if job["uploaded"]:
        transition_id = None
    else:
        groups = sample_cases(state)
        used = set(job["successful"])
        groups = {key: [t for t in values if t not in used] for key, values in groups.items()}
        groups = {key: values for key, values in groups.items() if values}
        if not groups:
            raise ValueError("No unseen transitions remain for the success streak")
        case_id = random.choice(list(groups))
        transition_id = random.choice(groups[case_id])
    sample = prepare_sample(state, transition_id, job["uploaded"])

    def save(state):
        current = job_record(state, job["id"])
        if current["status"] == "running":
            versions = sample["skill_versions"]
            if current.get("streak_versions") not in (None, versions):
                current.update(streak=0, successful=[])
            current["streak_versions"] = versions
            current.update(
                transition_id=transition_id,
                after_step=sample["after_step"],
                case_id=sample["case_id"],
                phase="predict",
                updated_at=now(),
            )

    app.state.store.mutate(save)
    evaluation = new_evaluation(app.state.store, job["id"], sample)
    if evaluation:
        launch(app, evaluation["id"])


def completed_output(app, job):
    evaluation_id = job["evaluation_id"]
    if not evaluation_id:
        return None
    launch(app, evaluation_id)  # recover a process restart between prepare and submission
    state = app.state.store.snapshot()
    fields = evaluation_record(state, evaluation_id)["fields"]
    if fields["status"] == "failed":
        raise ValueError(fields.get("error", "Tuning agent failed"))
    run = state["runs"].get(fields.get("run_id"))
    if not run:
        return None
    if run["status"] in {"queued", "running"}:
        call_service(app.state.settings, "agent", f"/internal/runs/{run['id']}/sync", {})
        run = app.state.store.snapshot()["runs"][run["id"]]
    if run["status"] in {"failed", "cancelled"}:
        raise ValueError(run.get("error", "Tuning agent did not finish"))
    if run["status"] != "done":
        return None
    if not run.get("final_message"):
        raise ValueError("Tuning agent returned no answer")
    return fields, run


def graded_prediction(app, job, fields, run):
    output = prediction(run["final_message"])
    if fields.get("status") == "graded":
        return output, {
            k: fields[k] for k in ("passed", "score", "explanation", "differences") if k in fields
        }
    if fields["expected"]:
        # Grade operational answer only; reasoning is retained for the correction agent.
        result = grade(fields["context"], fields["expected"], output["answer"])
        # A correct message format cannot compensate for the wrong operational action.
        result["passed"] = result["passed"] and all(
            result["scores"].get(dimension, 0) >= 80
            for dimension in ("action", "facts", "recipient_channel", "sequence")
        )
    else:
        result = {"explanation": "No reference step supplied; prediction only", "differences": []}

    def save(state):
        evaluation = evaluation_record(state, job["evaluation_id"])
        if job["uploaded"]:
            evaluation["fields"].update(
                **result, actual=json.dumps(output), status="graded", agent_provider=run["provider"]
            )
            return evaluation
        return update_in_state(
            state,
            evaluation["id"],
            {
                "version": evaluation["version"],
                "fields": {
                    **result,
                    "actual": json.dumps(output),
                    "status": "graded",
                    "agent_provider": run["provider"],
                },
            },
            "tuning",
            "Grade next-step prediction",
        )

    app.state.store.mutate(save)
    return output, result


def finish_prediction(app, job, fields, run):
    output, result = graded_prediction(app, job, fields, run)

    def save(state):
        current = job_record(state, job["id"])
        if current["status"] != "running":
            return
        versions = {
            s["id"]: s["current_version"]
            for s in state["skills"].values()
            if s.get("status") == "active"
        }
        if not current["uploaded"] and versions != fields["skill_versions"]:
            raise ConflictError(
                "Workflow skills changed during prediction; start a new tuning loop"
            )
        current["trials"] += 1
        row = {
            "id": job["evaluation_id"],
            "case_id": job["case_id"],
            "transition_id": job["transition_id"],
            "after_step": job["after_step"],
            **output,
            **result,
            "expected": fields["expected"],
            "skill_versions": fields["skill_versions"],
            "created_at": now(),
        }
        current["history"].append(row)
        current.update(last_result=row, evaluation_id=None, updated_at=now())
        if current["uploaded"]:
            current["status"] = "completed"
        elif result["passed"]:
            current["streak"] += 1
            current["successful"].append(job["transition_id"])
            current["phase"] = "sample"
            if current["streak"] >= current["target"]:
                current["status"] = "completed"
        else:
            # Keep successful cases for candidate regression testing, then reset streak.
            regressions = list(
                dict.fromkeys(r["transition_id"] for r in current["history"] if r.get("passed"))
            )[-10:]
            current.update(regressions=regressions, streak=0, successful=[], phase="revise")
        if current["status"] == "running" and current["trials"] >= current["max_trials"]:
            current["status"] = "exhausted"
        publish(state, "workflow_tuning.result", {"id": job["id"], "streak": current["streak"]})

    app.state.store.mutate(save)


def revision_sample(app, job):
    state = app.state.store.snapshot()
    sample = prepare_sample(state, job["transition_id"])
    # Reveal the answer only to the subsequent correction session, never the predictor.
    context = (
        REVISION_INSTRUCTIONS
        + "\n\n"
        + json.dumps(
            {
                "history": sample["context"],
                "failure": job["last_result"],
                "available_skills": [
                    {
                        "slug": s["slug"],
                        "name": s["name"],
                        "description": s["description"],
                        "current_version": s["current_version"],
                    }
                    for s in sample["state"]["skills"].values()
                ],
            },
            ensure_ascii=False,
        )
    )
    evaluation = new_evaluation(app.state.store, job["id"], sample, "revision", context)
    if evaluation:
        launch(app, evaluation["id"])


def candidate_sample(app, job):
    transition_id = job["transition_id"] if job["phase"] == "validate" else job["regressions"][0]
    sample = prepare_sample(app.state.store.snapshot(), transition_id, candidate=job["candidate"])
    evaluation = new_evaluation(app.state.store, job["id"], sample)
    if evaluation:
        launch(app, evaluation["id"])


def finish_revision(app, job, run):
    candidate = skill_candidate(app.state.store.snapshot(), run["final_message"])

    def save(state):
        current = job_record(state, job["id"])
        if current["status"] == "running":
            current.update(
                candidate=candidate, phase="validate", evaluation_id=None, updated_at=now()
            )

    app.state.store.mutate(save)


def publish_candidate(state, job):
    candidate = job["candidate"]
    key = f"skill:{candidate['slug']}"
    existing = state["skills"].get(key)
    version = existing["current_version"] if existing else 0
    if version != candidate["based_on_version"]:
        raise ConflictError("Skill changed during candidate tests; start a new tuning loop")
    # All tested skills must be unchanged, not just the edited workflow.
    versions = {
        s["id"]: s["current_version"]
        for s in state["skills"].values()
        if s.get("status") == "active"
    }
    if versions != job["last_result"]["skill_versions"]:
        raise ConflictError("Workflow skills changed during candidate tests")
    before = copy.deepcopy(existing)
    if not existing:
        create_in_state(
            state,
            {
                "id": key,
                "type": "skill",
                "name": candidate["name"],
                "description": candidate["summary"],
                "fields": {
                    "slug": candidate["slug"],
                    "source": "custom",
                    "status": "active",
                },
            },
            "tuning",
            candidate["summary"],
        )
        existing = state["skills"][key] = {
            "id": key,
            "slug": candidate["slug"],
            "name": candidate["name"],
            "description": candidate["summary"],
            "source": "custom",
            "status": "active",
            "current_version": 0,
            "content": "",
            "versions": [],
        }
    proposal = {
        "id": identifier("skill_change_proposal"),
        "skill_id": key,
        "based_on_version": version,
        "proposed_content": candidate["content"],
        "reasoning": candidate["summary"],
        "expected_effect": candidate["summary"],
        "risks": "Automatically tested training correction",
        "issues": [],
        "proposed_by": job["id"],
        "status": "approved",
        "reviewed_by": "workflow-tuner",
        "reviewed_at": now(),
        "created_at": now(),
        "validation": job["validation"],
    }
    published_version = publish_version(state, existing, proposal)
    proposal["published_version"] = published_version
    state["proposals"][proposal["id"]] = proposal
    version_id = f"skill_version:{candidate['slug']}-v{published_version}"
    add_edge(state, version_id, job["case_id"], "learned_from")
    add_edge(state, job["case_id"], key, "exercises")
    record_change(state, "skill.auto_published", job["id"], candidate["summary"], before, existing)
    job["changes"].append(
        {
            "skill_id": key,
            "version": published_version,
            "summary": candidate["summary"],
            "old_text": candidate["old_text"],
            "new_text": candidate["new_text"],
            "validation": job["validation"],
            "created_at": now(),
        }
    )


def finish_validation(app, job, fields, run):
    output, result = graded_prediction(app, job, fields, run)

    def save(state):
        current = job_record(state, job["id"])
        if current["status"] != "running":
            return
        evidence = {
            "evaluation_id": job["evaluation_id"],
            "phase": job["phase"],
            **output,
            **result,
        }
        current.setdefault("validation", []).append(evidence)
        if not result["passed"]:
            current["rejected"].append(
                {
                    "candidate": current.pop("candidate"),
                    "validation": current.pop("validation"),
                    "created_at": now(),
                }
            )
            current.update(phase="sample", evaluation_id=None, updated_at=now())
            return
        if job["phase"] == "regress":
            current["regressions"].pop(0)
        if current["regressions"]:
            current.update(phase="regress", evaluation_id=None, updated_at=now())
            return
        publish_candidate(state, current)
        current.pop("candidate", None)
        current.pop("validation", None)
        current.update(phase="sample", evaluation_id=None, updated_at=now())

    app.state.store.mutate(save)


def advance(app, key):
    """One bounded phase per invocation; generation-matched leases prevent double advancement."""
    lease = identifier("lease")

    def claim(state):
        job = job_record(state, key)
        if job["status"] != "running" or job["lease_until"] > time.time():
            return None
        job.update(lease=lease, lease_until=time.time() + 300, last_tick_at=time.time())
        return job

    job = app.state.store.mutate(claim)
    if not job:
        return
    try:
        if not job["evaluation_id"]:
            if job["phase"] == "sample":
                sample_job(app, job)
            elif job["phase"] == "revise":
                revision_sample(app, job)
            elif job["phase"] == "predict":
                sample = prepare_sample(
                    app.state.store.snapshot(), job["transition_id"], job["uploaded"]
                )
                evaluation = new_evaluation(app.state.store, key, sample)
                if evaluation:
                    launch(app, evaluation["id"])
            else:
                candidate_sample(app, job)
        else:
            completed = completed_output(app, job)
            if completed:
                fields, run = completed
                if job["phase"] == "predict":
                    finish_prediction(app, job, fields, run)
                elif job["phase"] == "revise":
                    finish_revision(app, job, run)
                else:
                    finish_validation(app, job, fields, run)
    except Exception as exc:
        error = str(exc)[:2000]

        def fail(state):
            current = job_record(state, key)
            if current["status"] == "running" and current.get("lease") == lease:
                current.update(status="failed", error=error, updated_at=now())
                if current.get("evaluation_id"):
                    run_id = evaluation_record(state, current["evaluation_id"])["fields"].get(
                        "run_id"
                    )
                    if run_id:
                        state.setdefault("mcp_sessions", {}).get(run_id, {})["revoked"] = True

        app.state.store.mutate(fail)
    finally:

        def release(state):
            current = job_record(state, key)
            if current.get("lease") == lease:
                current.update(lease_until=0)

        app.state.store.mutate(release)


def tick(app):
    pending = sorted(
        (
            j
            for j in app.state.store.snapshot()["workflow_tuning_jobs"].values()
            if j["status"] == "running"
        ),
        key=lambda j: j.get("last_tick_at", 0),
    )
    # Bound each Cloud Scheduler HTTP invocation and rotate fairly through private tests.
    jobs = [j["id"] for j in pending[:2]]
    for key in jobs:
        advance(app, key)
    return {"advanced": jobs}
