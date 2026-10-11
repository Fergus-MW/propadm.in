"""Admin ingestion, versioned workflow publication and production-agent replay evaluation."""

import copy
import json
import re

from fastapi import APIRouter, Depends, Request
from propadmin_core.graph import add_edge, create_in_state, record_change, update_in_state
from propadmin_core.store import ConflictError, identifier, now
from propadmin_core.workflow_corpus import RUBRIC_VERSION, WorkflowCorpus
from propadmin_core.workflow_judge import grade
from propadmin_core.workflow_replay import prepare_replay
from propadmin_core.workflow_triplets import KINDS, enrich_case, index_status, retrieve_examples
from pydantic import Field

from .auth import require_admin
from .models import Input
from .routes_agent import publish_version
from .services import call_service

router = APIRouter(prefix="/v1", dependencies=[Depends(require_admin)])


class Source(Input):
    path: str = Field(min_length=1, max_length=500)
    mime: str = "text/markdown"
    content_base64: str = Field(max_length=7_000_000)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class CaseImport(Input):
    dataset: str = Field(min_length=1, max_length=70, pattern=r"^[a-z][a-z0-9_-]+$")
    case_ref: str = Field(pattern=r"^\d{3}$")
    sources: list[Source] = Field(min_length=2, max_length=100)


class SkillPublish(Input):
    slug: str = Field(pattern=r"^[a-z][a-z0-9-]+$", max_length=100)
    name: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=30, max_length=100_000)
    summary: str = Field(min_length=1, max_length=4000)
    based_on_version: int = Field(ge=0)
    training_cases: list[str] = Field(min_length=1, max_length=100)


class Prepare(Input):
    transition_id: str = Field(max_length=200)


class ExampleSearch(Input):
    query: str = Field(min_length=1, max_length=12000)
    limit: int = Field(default=5, ge=1, le=20)
    exclude_case_id: str | None = None
    tags: list[str] = Field(default_factory=list, max_length=10)


@router.post("/workflow-cases/{case_id}/triplets")
def extract_triplets(case_id: str, request: Request):
    return enrich_case(request.app.state.store, case_id)


@router.get("/workflow-triplets")
def triplets(request: Request, case_id: str | None = None):
    return {"items": [e for e in request.app.state.graph.list_entities(type="workflow_triplet")
                      if not case_id or e["fields"]["case_id"] == case_id]}


@router.get("/workflow-triplets/status")
def triplet_status(request: Request):
    return index_status(request.app.state.store.snapshot())


def example_search(app, session_id, args):
    payload = ExampleSearch(**args)
    if set(payload.tags) - KINDS:
        raise ValueError("Unknown triplet metadata tag")
    return retrieve_examples(app.state.store.snapshot(), **payload.model_dump())


@router.post("/workflow-examples/search")
def examples(payload: ExampleSearch, request: Request):
    return example_search(request.app, "admin", payload.model_dump())


TOOLS = {"search_workflow_examples": {
    "description": "Find prior training-case conversation triplets by similarity to their first TWO steps. "
                   "Returns actions, decisions, insights, grounded metadata and the observed third step. "
                   "Use these as examples, not live case facts. Holdout cases are excluded. Supply the current "
                   "case id to exclude its entire history. Replay already contains only permitted examples.",
    "input_schema": {"type": "object", "properties": {
        "query": {"type": "string", "minLength": 1, "maxLength": 12000},
        "limit": {"type": "integer", "minimum": 1, "maximum": 20},
        "exclude_case_id": {"type": "string", "maxLength": 200},
        "tags": {"type": "array", "items": {"type": "string", "maxLength": 100}, "maxItems": 10},
    }, "required": ["query"], "additionalProperties": False},
    "annotations": {"readOnlyHint": True, "destructiveHint": False}, "handler": example_search,
}}


@router.post("/workflow-cases/import", status_code=201)
def import_case(payload: CaseImport, request: Request):
    return WorkflowCorpus(request.app.state.store).ingest(
        payload.dataset, payload.case_ref, [s.model_dump() for s in payload.sources]
    )


@router.get("/workflow-cases")
def cases(request: Request, dataset: str | None = None, split: str | None = None):
    return {"items": [e for e in request.app.state.graph.list_entities(type="workflow_case")
                      if (not dataset or e["fields"]["dataset"] == dataset)
                      and (not split or e["fields"]["split"] == split)]}


@router.get("/workflow-transitions")
def transitions(request: Request, case_id: str | None = None, evaluable: bool | None = None):
    return {"items": [e for e in request.app.state.graph.list_entities(type="workflow_transition")
                      if (not case_id or e["fields"]["case_id"] == case_id)
                      and (evaluable is None or e["fields"]["evaluable"] == evaluable)]}


@router.post("/workflow-skills/publish")
def publish_skill(payload: SkillPublish, request: Request):
    if not re.match(rf"---\s*\nname: {re.escape(payload.slug)}\s*\n", payload.content):
        raise ValueError("Skill content needs matching name frontmatter")

    def write(state):
        for case_id in payload.training_cases:
            case = state["entities"][case_id]
            if case["type"] != "workflow_case" or case["fields"]["split"] != "training":
                raise ValueError("Skill evidence must use training cases; holdout cases stay unseen")
        key = f"skill:{payload.slug}"
        existing = state["skills"].get(key)
        current = existing["current_version"] if existing else 0
        if payload.based_on_version != current:
            raise ConflictError(f"Stale skill version; current is {current}")
        if existing and existing["content"] == payload.content:
            version_id = f"skill_version:{payload.slug}-v{current}"
            for case_id in payload.training_cases:
                add_edge(state, version_id, case_id, "learned_from")
                add_edge(state, case_id, key, "exercises")
            return {"id": key, "version": current, "deduplicated": True}
        before = copy.deepcopy(existing)
        if not existing:
            create_in_state(state, {"id": key, "type": "skill", "name": payload.name,
                "description": payload.summary, "fields": {
                    "slug": payload.slug, "source": "custom", "status": "active",
                }}, "admin", payload.summary)
            existing = state["skills"][key] = {
                "id": key, "slug": payload.slug, "name": payload.name,
                "description": payload.summary, "source": "custom", "status": "active",
                "current_version": 0, "content": "", "versions": [],
            }
        proposal = {
            "id": identifier("skill_change_proposal"), "skill_id": key,
            "based_on_version": current, "proposed_content": payload.content,
            "reasoning": payload.summary, "expected_effect": payload.summary,
            "risks": "Training-derived workflow; holdout history excluded from publication",
            "issues": [], "proposed_by": "admin", "status": "approved",
            "reviewed_by": "admin", "reviewed_at": now(), "created_at": now(),
            "training_cases": payload.training_cases,
        }
        version = publish_version(state, existing, proposal)
        proposal["published_version"] = version
        state["proposals"][proposal["id"]] = proposal
        version_id = f"skill_version:{payload.slug}-v{version}"
        for case_id in payload.training_cases:
            add_edge(state, version_id, case_id, "learned_from")
            add_edge(state, case_id, key, "exercises")
        record_change(state, "skill.published", "admin", payload.summary, before, existing)
        return {"id": key, "version": version, "deduplicated": False}

    return request.app.state.store.mutate(write)


@router.post("/workflow-evaluations", status_code=201)
def prepare(payload: Prepare, request: Request):
    # Build embeddings outside CAS callback; no provider call is repeated on CAS retry.
    state = request.app.state.store.snapshot()
    replay = prepare_replay(state, payload.transition_id)
    transition = state["entities"][payload.transition_id]
    evaluation_id = identifier("workflow_evaluation")

    def write(state):
        entity = create_in_state(state, {"id": evaluation_id, "type": "workflow_evaluation",
            "name": f"Replay {transition['name']}", "fields": {
                "transition_id": payload.transition_id, "case_id": transition["fields"]["case_id"],
                "status": "prepared", "context_hash": replay["context_hash"],
                "context": replay["context"], "expected": replay["expected"],
                "skill_versions": replay["skill_versions"], "rubric_version": RUBRIC_VERSION,
            }}, "admin", "Prepare isolated production-agent replay")
        state["workflow_sandboxes"][evaluation_id] = replay["state"]
        add_edge(state, evaluation_id, payload.transition_id, "evaluates")
        for key, version in replay["skill_versions"].items():
            version_id = f"skill_version:{key.split(':', 1)[1]}-v{version}"
            if version_id in state["entities"]:
                add_edge(state, evaluation_id, version_id, "used_skill")
        return entity

    return request.app.state.store.mutate(write)


@router.post("/workflow-evaluations/{evaluation_id}/run", status_code=201)
def run(evaluation_id: str, request: Request):
    evaluation = request.app.state.graph.get_entity(evaluation_id)
    if evaluation["type"] != "workflow_evaluation" or evaluation["fields"]["status"] != "prepared":
        raise ConflictError("This evaluation has already been submitted")
    return call_service(request.app.state.settings, "agent", "/internal/runs", {
        "goal": "Reproduce the single next operational step from the historical prefix.",
        "subjects": [], "evaluation_id": evaluation_id,
    }, timeout=240)


@router.post("/workflow-evaluations/{evaluation_id}/grade")
def grade_run(evaluation_id: str, request: Request):
    state = request.app.state.store.snapshot()
    evaluation = state["entities"][evaluation_id]
    if evaluation["type"] != "workflow_evaluation":
        raise ValueError("Expected workflow evaluation")
    if evaluation["fields"]["status"] == "graded":
        return evaluation
    run = state["runs"][evaluation["fields"]["run_id"]]
    if run["status"] != "done":
        raise ValueError("Only a completed production-agent run can be graded")
    sandbox = state["workflow_sandboxes"][evaluation_id]
    from .workflow_sandbox import CAPTURE_TOOLS

    observable = CAPTURE_TOOLS | {"upsert_entity", "update_entity", "link_entities",
                                 "unlink_entities", "merge_entities", "add_note"}
    captured = [a for a in sandbox["actions"].values() if a.get("tool") in observable]
    actual = json.dumps({"final_message": run.get("final_message"), "actions": captured}, ensure_ascii=False)
    if not run.get("final_message") and not captured:
        raise ValueError("No observable agent output to grade")
    result = grade(evaluation["fields"]["context"], evaluation["fields"]["expected"], actual)

    def write(state):
        current = state["entities"][evaluation_id]
        if current["fields"]["status"] == "graded":
            return current
        return update_in_state(state, evaluation_id, {"version": current["version"], "fields": {
            **result, "actual": actual, "status": "graded", "agent_provider": run["provider"],
        }}, "admin", "Haiku comparison against recorded next step")

    return request.app.state.store.mutate(write)


@router.get("/workflow-evaluations")
def evaluations(request: Request):
    return {"items": request.app.state.graph.list_entities(type="workflow_evaluation")}
