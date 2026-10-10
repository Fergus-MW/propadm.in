"""Evaluation MCP calls see only a persisted temporal sandbox; no service side effects."""

import copy
from types import SimpleNamespace

from propadmin_core import GraphService, ProviderNotConfigured, SearchService
from propadmin_core.store import identifier

from .services import record_action

PLAN_TOOLS = {"get_plan", "create_plan", "update_step", "add_step", "revise_plan", "get_skill",
              "list_workflow_issues"}
CAPTURE_TOOLS = {"send_email", "reply_email", "place_call", "create_ticket", "update_ticket",
                 "update_crm_record", "sleep", "schedule_invocation", "cancel_invocation"}
GRAPH_TOOLS = {"search", "get_entity", "traverse", "get_document", "upsert_entity", "update_entity",
               "link_entities", "unlink_entities", "merge_entities", "add_note", "search_workflow_examples"}


class ReplayStore:
    def __init__(self, store, evaluation_id, run):
        self.store, self.evaluation_id, self.run = store, evaluation_id, run

    def read(self, fn):
        return fn(self.snapshot())  # snapshot() is already a private filtered copy

    def snapshot(self):
        state = self.store.snapshot()
        sandbox = copy.deepcopy(state["workflow_sandboxes"][self.evaluation_id])
        if "tuning_view" in sandbox:
            from propadmin_core.workflow_tuning import isolated_graph

            view = sandbox["tuning_view"]
            permitted = isolated_graph(state, view["case_id"])
            permitted["skills"] = view["skills"]
            permitted["entities"] = {k: e for k, e in permitted["entities"].items()
                                      if e["type"] not in {"skill", "skill_version"}}
            permitted["entities"].update(view["skill_entities"])
            permitted["embeddings"] = {k: e for k, e in permitted["embeddings"].items()
                                        if not e["owner"].startswith(("skill:", "skill_version:"))}
            for collection in ("runs", "actions", "plans"):
                permitted[collection] = sandbox[collection]
            sandbox = permitted
        sandbox["runs"].setdefault(self.run["id"], copy.deepcopy(self.run))
        return sandbox

    def mutate(self, callback):
        def write(state):
            sandbox = state["workflow_sandboxes"][self.evaluation_id]
            sandbox["runs"].setdefault(self.run["id"], copy.deepcopy(self.run))
            return callback(sandbox)

        return self.store.mutate(write)


def execute_replay(request, name, args, run, execute):
    if run.get("kind") == "tuning":
        from propadmin_core.workflow_tuning import READ_TOOLS

        if name not in READ_TOOLS:
            raise ProviderNotConfigured(f"{name} is unavailable to the performance tuning agent")
    store = ReplayStore(request.app.state.store, run["evaluation_id"], run)
    if name in CAPTURE_TOOLS:
        payload = {"status": "captured", "simulated": True, "external_execution": False,
                   "id": identifier("replay_action"), "tool": name}
        record_action(store, run["id"], name, args, payload, args.get("reason", ""))
        return payload
    if name not in GRAPH_TOOLS | PLAN_TOOLS:
        raise ProviderNotConfigured(f"{name} is unavailable in isolated historical replay")
    app = SimpleNamespace(state=SimpleNamespace(
        store=store, graph=GraphService(store), search=SearchService(store),
        settings=request.app.state.settings, telemetry=request.app.state.telemetry,
    ))
    response = execute(SimpleNamespace(app=app), name, args, run["id"], False)
    record_action(store, run["id"], name, args, response, args.get("reason", ""))
    return response
