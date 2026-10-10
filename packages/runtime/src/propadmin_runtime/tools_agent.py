"""Plan, sleep and skill MCP tools for the one sandboxed agent. handler(app, run_id, args) -> dict."""

import copy
import difflib
from datetime import datetime, timedelta, timezone

import httpx
from propadmin_core import ProviderNotConfigured
from propadmin_core.store import identifier, now, publish

from .services import call_service, record_action

STEP_STATUSES = {"pending", "in_progress", "done", "blocked", "skipped"}
ISSUE_CATEGORIES = {
    "wrong_step",
    "missing_step",
    "outdated_info",
    "ambiguous_instruction",
    "tool_failure",
    "policy_gap",
}
SEVERITIES = {"low", "medium", "high", "critical"}
MAX_SLEEP_MINUTES = 10  # PRD: mandatory 10-minute timeout, the agent always wakes


def text(max_length=4000):
    return {"type": "string", "minLength": 1, "maxLength": max_length}


def schema(properties, required=()):
    return {
        "type": "object",
        "properties": properties,
        "required": list(required),
        "additionalProperties": False,
    }


STEP_INPUT = schema(
    {"id": text(100), "title": text(500), "detail": {"type": "string", "maxLength": 4000}},
    ["title"],
)


def later(minutes):
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


def schedule_wakeup(state, run_id, minutes, wake_on=(), reason=""):
    """Replace the run's pending wakeup; the agent service fires it (Cloud Tasks / due sweep)."""
    for wakeup in state["wakeups"].values():
        if wakeup["run_id"] == run_id and wakeup["status"] == "pending":
            wakeup["status"] = "superseded"
    wakeup = {
        "id": identifier("wakeup"),
        "run_id": run_id,
        "due_at": later(minutes),
        "minutes": minutes,
        "wake_on": list(wake_on),
        "reason": reason,
        "status": "pending",
        "created_at": now(),
    }
    state["wakeups"][wakeup["id"]] = wakeup
    run = state["runs"][run_id]
    run.update(status="sleeping", next_wake_at=wakeup["due_at"], updated_at=now())
    publish(state, "agent_run.sleeping", {"run_id": run_id, "due_at": wakeup["due_at"]})
    return wakeup


def plan_complete(plan):
    return plan is None or all(s["status"] in {"done", "skipped"} for s in plan["steps"])


def make_step(item, index):
    return {
        "id": item.get("id") or f"step-{index}",
        "title": item["title"],
        "detail": item.get("detail", ""),
        "status": "pending",
        "note": "",
        "evidence": None,
    }


def mutate_plan(app, run_id, change):
    """Apply change(plan) to the run's plan, bump its version and keep the previous revision."""

    def write(state):
        run = state["runs"][run_id]
        plan = state["plans"].get(run.get("plan_id") or "")
        if plan is None:
            raise ValueError("This run has no plan yet; call create_plan first")
        previous = copy.deepcopy({k: plan[k] for k in ("steps", "version", "goal")})
        change(plan)
        plan.setdefault("history", []).append(previous)
        plan["history"] = plan["history"][-50:]
        plan.update(version=plan["version"] + 1, updated_at=now())
        run["updated_at"] = now()
        publish(state, "plan.updated", {"run_id": run_id, "plan_id": plan["id"]})
        return plan

    return app.state.store.mutate(write)


def create_plan(app, run_id, args):
    def write(state):
        run = state["runs"][run_id]
        if run.get("plan_id"):
            raise ValueError("This run already has a plan; use revise_plan or add_step")
        steps = [make_step(item, i + 1) for i, item in enumerate(args["steps"])]
        if len({s["id"] for s in steps}) != len(steps):
            raise ValueError("Step ids must be unique")
        plan = {
            "id": identifier("plan"),
            "run_id": run_id,
            "goal": args["goal"],
            "steps": steps,
            "version": 1,
            "history": [],
            "created_at": now(),
            "updated_at": now(),
        }
        state["plans"][plan["id"]] = plan
        run.update(plan_id=plan["id"], updated_at=now())
        publish(state, "plan.created", {"run_id": run_id, "plan_id": plan["id"]})
        return plan

    return app.state.store.mutate(write)


def get_plan(app, run_id, args):
    state = app.state.store.snapshot()
    plan = state["plans"].get(state["runs"][run_id].get("plan_id") or "")
    return plan or {"plan": None, "hint": "No plan yet; create_plan before multi-step work"}


def update_step(app, run_id, args):
    status = args["status"]
    if status not in STEP_STATUSES:
        raise ValueError(f"status must be one of {sorted(STEP_STATUSES)}")

    def change(plan):
        step = next((s for s in plan["steps"] if s["id"] == args["step_id"]), None)
        if step is None:
            raise ValueError("Unknown step_id")
        if status == "in_progress" and any(
            s["status"] == "in_progress" and s is not step for s in plan["steps"]
        ):
            raise ValueError("Only one step may be in_progress; finish or block the current one")
        if status == "done" and not args.get("evidence"):
            raise ValueError("A step is done only with evidence: attach the tool result")
        if status in {"blocked", "skipped"} and not args.get("note"):
            raise ValueError("Blocked and skipped steps need a note saying why")
        step.update(status=status, note=args.get("note", step["note"]))
        if args.get("evidence"):
            step["evidence"] = args["evidence"]

    return mutate_plan(app, run_id, change)


def add_step(app, run_id, args):
    def change(plan):
        step = make_step(args, len(plan["steps"]) + 1)
        if any(s["id"] == step["id"] for s in plan["steps"]):
            step["id"] = identifier("step")
        ids = [s["id"] for s in plan["steps"]]
        after = args.get("after")
        if after and after not in ids:
            raise ValueError("Unknown step id in after")
        plan["steps"].insert(ids.index(after) + 1 if after else len(ids), step)

    return mutate_plan(app, run_id, change)


def revise_plan(app, run_id, args):
    """Replace step order/content; steps that keep their id keep their status and evidence."""

    def change(plan):
        existing = {s["id"]: s for s in plan["steps"]}
        steps = []
        for index, item in enumerate(args["steps"], 1):
            kept = existing.get(item.get("id"))
            if kept:
                steps.append({**kept, "title": item["title"], "detail": item.get("detail", "")})
            else:
                steps.append(make_step({**item, "id": item.get("id") or identifier("step")}, index))
        if sum(s["status"] == "in_progress" for s in steps) > 1:
            raise ValueError("Only one step may be in_progress")
        plan.update(
            steps=steps, goal=args.get("goal", plan["goal"]), revision_reason=args["reason"]
        )

    return mutate_plan(app, run_id, change)


def sleep(app, run_id, args):
    minutes = min(args.get("minutes", MAX_SLEEP_MINUTES), MAX_SLEEP_MINUTES)

    def write(state):
        run = state["runs"][run_id]
        plan = state["plans"].get(run.get("plan_id") or "")
        if (
            plan
            and not plan_complete(plan)
            and not any(s["status"] in {"in_progress", "blocked"} for s in plan["steps"])
        ):
            raise ValueError(
                "Before sleeping leave the current step in_progress or blocked with what it waits for"
            )
        run["subjects"] = sorted(set(run["subjects"]) | set(args.get("wake_on", [])))
        return schedule_wakeup(state, run_id, minutes, args.get("wake_on", []), args["reason"])

    wakeup = app.state.store.mutate(write)
    try:  # a browser session never stays open across a sleep
        call_service(app.state.settings, "browser", f"/internal/sessions/{run_id}/close")
    except (ProviderNotConfigured, ValueError, httpx.HTTPError):
        pass
    return {**wakeup, "instruction": "End your turn now; you will be woken with the reason."}


def skill_record(state, slug):
    skill = state["skills"].get(slug if slug.startswith("skill:") else f"skill:{slug}")
    if skill is None:
        raise KeyError(slug)
    return skill


def get_skill(app, run_id, args):
    skill = skill_record(app.state.store.snapshot(), args["skill"])
    version = args.get("version", skill["current_version"])
    match = next((v for v in skill["versions"] if v["version"] == version), None)
    if match is None and version != skill["current_version"]:
        raise ValueError("Unknown skill version")
    return {
        "id": skill["id"],
        "slug": skill["slug"],
        "version": version,
        "content": (match or skill)["content"],
    }


def list_workflow_issues(app, run_id, args):
    state = app.state.store.snapshot()
    skill = skill_record(state, args["skill"])
    items = [
        issue
        for issue in state["issues"].values()
        if issue["skill_id"] == skill["id"] and issue["status"] in {"open", "proposal_pending"}
    ]
    return {"items": sorted(items, key=lambda i: (-i["occurrences"], i["created_at"]))}


def report_workflow_issue(app, run_id, args):
    if args["category"] not in ISSUE_CATEGORIES or args["severity"] not in SEVERITIES:
        raise ValueError(
            f"category must be one of {sorted(ISSUE_CATEGORIES)}; severity one of {sorted(SEVERITIES)}"
        )

    def write(state):
        skill = skill_record(state, args["skill"])
        # ponytail: duplicate match on normalised title, swap for embedding similarity when
        # issues are embedded in the graph.
        key = args["title"].casefold().strip()
        issue = next(
            (
                i
                for i in state["issues"].values()
                if i["skill_id"] == skill["id"]
                and i["status"] in {"open", "proposal_pending"}
                and i["title"].casefold().strip() == key
            ),
            None,
        )
        evidence = {"run_id": run_id, "text": args["evidence"], "at": now()}
        related = args.get("related_entities", [])
        if issue:
            issue["occurrences"] += 1
            issue["evidence"].append(evidence)
            issue["related_entities"] = sorted(set(issue["related_entities"]) | set(related))
            issue["found_in"] = sorted(set(issue["found_in"]) | {run_id})
        else:
            issue = {
                "id": identifier("workflow_issue"),
                "skill_id": skill["id"],
                "skill_version": skill["current_version"],
                "title": args["title"],
                "description": args["description"],
                "evidence": [evidence],
                "category": args["category"],
                "severity": args["severity"],
                "status": "open",
                "occurrences": 1,
                "related_entities": related,
                "found_in": [run_id],
                "created_at": now(),
            }
            state["issues"][issue["id"]] = issue
        issue["updated_at"] = now()
        publish(state, "workflow_issue.reported", {"id": issue["id"], "run_id": run_id})
        return issue

    return app.state.store.mutate(write)


def propose_skill_change(app, run_id, args):
    if not args["issues"]:
        raise ValueError("A proposal must reference at least one workflow issue")

    def write(state):
        skill = skill_record(state, args["skill"])
        for issue_id in args["issues"]:
            issue = state["issues"].get(issue_id)
            if not issue or issue["skill_id"] != skill["id"]:
                raise ValueError(f"{issue_id} is not a workflow issue on this skill")
        diff = "".join(
            difflib.unified_diff(
                skill["content"].splitlines(keepends=True),
                args["proposed_content"].splitlines(keepends=True),
                f"v{skill['current_version']}",
                "proposed",
            )
        )
        proposal = {
            "id": identifier("skill_change_proposal"),
            "skill_id": skill["id"],
            "based_on_version": skill["current_version"],
            "proposed_content": args["proposed_content"],
            "diff": diff,
            "reasoning": args["reasoning"],
            "expected_effect": args["expected_effect"],
            "risks": args["risks"],
            "issues": args["issues"],
            "status": "pending_review",
            "proposed_by": run_id,
            "review_notes": "",
            "reviewed_by": None,
            "reviewed_at": None,
            "created_at": now(),
        }
        state["proposals"][proposal["id"]] = proposal
        for issue_id in args["issues"]:
            state["issues"][issue_id]["status"] = "proposal_pending"
        # The proposal becomes a subject so review feedback routes back to this run.
        state["runs"][run_id]["subjects"].append(proposal["id"])
        publish(state, "skill_proposal.created", {"id": proposal["id"], "run_id": run_id})
        return proposal

    return app.state.store.mutate(write)


def logged(name, handler):
    def run(app, run_id, args):
        try:
            result = handler(app, run_id, args)
        except (KeyError, ValueError) as exc:
            record_action(
                app.state.store, run_id, name, args, reason=args.get("reason", ""), error=str(exc)
            )
            raise
        record_action(
            app.state.store, run_id, name, args, result={"ok": True}, reason=args.get("reason", "")
        )
        return result

    return run


SPECS = {
    "create_plan": (
        create_plan,
        "Create the run's plan before any multi-step task. Steps start pending.",
        schema(
            {"goal": text(2000), "steps": {"type": "array", "items": STEP_INPUT, "maxItems": 50}},
            ["goal", "steps"],
        ),
    ),
    "get_plan": (
        get_plan,
        "Return the plan with step statuses; call first on every wake-up.",
        schema({}),
    ),
    "update_step": (
        update_step,
        "Move a step pending -> in_progress -> done (evidence required), or blocked/skipped "
        "with a note. Only one step may be in_progress.",
        schema(
            {
                "step_id": text(100),
                "status": text(20),
                "note": {"type": "string", "maxLength": 4000},
                "evidence": {"type": "string", "maxLength": 20000},
            },
            ["step_id", "status"],
        ),
    ),
    "add_step": (
        add_step,
        "Add a step, optionally after an existing step id. The previous plan version is kept.",
        schema(
            {
                "title": text(500),
                "detail": {"type": "string", "maxLength": 4000},
                "after": text(100),
            },
            ["title"],
        ),
    ),
    "revise_plan": (
        revise_plan,
        "Reorder or rewrite steps; steps keeping their id keep status. Previous version kept.",
        schema(
            {
                "goal": text(2000),
                "reason": text(2000),
                "steps": {"type": "array", "items": STEP_INPUT, "maxItems": 50},
            },
            ["steps", "reason"],
        ),
    ),
    "sleep": (
        sleep,
        "Pause this task and end your turn. Wakes when an event about any wake_on subject "
        "(thread, call, ticket or entity id) arrives, or after minutes (max 10).",
        schema(
            {
                "minutes": {"type": "integer", "minimum": 1, "maximum": MAX_SLEEP_MINUTES},
                "wake_on": {"type": "array", "items": text(500), "maxItems": 50},
                "reason": text(2000),
            },
            ["reason"],
        ),
    ),
    "get_skill": (
        get_skill,
        "Read a skill's SKILL.md by slug, current version unless version is given.",
        schema(
            {"skill": text(200), "version": {"type": "integer", "minimum": 1, "maximum": 100000}},
            ["skill"],
        ),
    ),
    "list_workflow_issues": (
        list_workflow_issues,
        "List open workflow issues on a skill, most frequent first.",
        schema({"skill": text(200)}, ["skill"]),
    ),
    "report_workflow_issue": (
        report_workflow_issue,
        "Report a workflow problem with a skill (see workflow-review). Duplicates increment "
        "occurrences. category: "
        + ", ".join(sorted(ISSUE_CATEGORIES))
        + "; severity: "
        + ", ".join(sorted(SEVERITIES))
        + ".",
        schema(
            {
                "skill": text(200),
                "title": text(500),
                "description": text(),
                "evidence": text(),
                "category": text(50),
                "severity": text(20),
                "related_entities": {"type": "array", "items": text(500), "maxItems": 50},
            },
            ["skill", "title", "description", "evidence", "category", "severity"],
        ),
    ),
    "propose_skill_change": (
        propose_skill_change,
        "Propose a full new SKILL.md against the current version, citing at least one issue. "
        "An admin reviews it; you never edit a live skill.",
        schema(
            {
                "skill": text(200),
                "proposed_content": text(100000),
                "reasoning": text(),
                "expected_effect": text(),
                "risks": text(),
                "issues": {"type": "array", "items": text(200), "maxItems": 50},
            },
            ["skill", "proposed_content", "reasoning", "expected_effect", "risks", "issues"],
        ),
    ),
}

TOOLS = {
    name: {
        "description": description,
        "input_schema": input_schema,
        "handler": logged(name, handler),
    }
    for name, (handler, description, input_schema) in SPECS.items()
}
