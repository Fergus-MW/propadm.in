"""Import cases, publish evidenced skills, and run next-step comparisons in production."""

import argparse
import base64
import hashlib
import json
import mimetypes
import time
from pathlib import Path

import httpx

from .gateway import Gateway


def sources(folder):
    return [{"path": str(file.relative_to(folder)),
             "mime": mimetypes.guess_type(file.name)[0] or "application/octet-stream",
             "content_base64": base64.b64encode(file.read_bytes()).decode(),
             "sha256": hashlib.sha256(file.read_bytes()).hexdigest()}
            for file in sorted(folder.rglob("*")) if file.is_file() and not file.name.startswith(".")]


def import_cases(gateway, root, dataset, receipt):
    folders = sorted(folder for folder in root.iterdir() if folder.is_dir() and (folder / "index.md").exists())
    if not folders:
        raise ValueError("No case folders found")
    result = {"dataset": dataset, "cases": [], "errors": []}
    for folder in folders:
        try:
            response = gateway.request("POST", "/v1/workflow-cases/import", {
                "dataset": dataset, "case_ref": folder.name, "sources": sources(folder),
            })
            result["cases"].append(response)
            print(folder.name, "deduplicated" if response.get("deduplicated") else f"{response['events']} events", flush=True)
        except Exception as exc:
            result["errors"].append({"case_ref": folder.name, "error": str(exc)})
            print(folder.name, "FAILED:", str(exc), flush=True)
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_text(json.dumps(result, indent=2))
    return result


def publish_skills(gateway, dataset, root):
    cases = gateway.request("GET", "/v1/workflow-cases", query={"dataset": dataset, "split": "training"})["items"]
    existing = {s["slug"]: s for s in gateway.request("GET", "/v1/skills")["items"]}
    selected = {"property-case-resolution", "checkout-works", "resolve-maintenance-email", "contractor-invoice"}
    result = []
    for slug in sorted(selected):
        content = (root / slug / "SKILL.md").read_text()
        evidence = [c["id"] for c in cases if slug in c["fields"]["skills"]]
        response = gateway.request("POST", "/v1/workflow-skills/publish", {
            "slug": slug, "name": slug.replace("-", " ").title(), "content": content,
            "summary": "Historical case workflows: prior approvals, scope, access, quote comparison and evidence-based completion",
            "based_on_version": existing.get(slug, {}).get("current_version", 0), "training_cases": evidence,
        })
        result.append(response)
        print(slug, response, flush=True)
    return result


def retry_safe(gateway, method, path, body=None):
    """Retry reads, sync and idempotent grading; never blindly repeat run submission."""
    for attempt in range(5):
        try:
            return gateway.request(method, path, body)
        except (ValueError, httpx.HTTPError):
            if attempt == 4:
                raise
            time.sleep(2 ** attempt)


def evaluate(gateway, transition, timeout):
    evaluation = gateway.request("POST", "/v1/workflow-evaluations", {"transition_id": transition["id"]})
    evaluation_id = evaluation["id"]
    print(transition["name"], "prepared", evaluation_id, flush=True)
    try:
        run = gateway.request("POST", f"/v1/workflow-evaluations/{evaluation_id}/run", {})
    except (ValueError, httpx.HTTPError):
        # An HTTP timeout can arrive after the production session was created.
        # Recover that run instead of starting a second billable session.
        saved = retry_safe(gateway, "GET", f"/v1/entities/{evaluation_id}")
        run_id = saved["fields"].get("run_id")
        if not run_id:
            raise
        run = retry_safe(gateway, "GET", f"/v1/agent-runs/{run_id}")
    deadline = time.monotonic() + timeout
    print(transition["name"], evaluation_id, run["id"], flush=True)
    while run["status"] in {"running", "queued", "sleeping"}:
        if time.monotonic() >= deadline:
            retry_safe(gateway, "POST", f"/v1/agent-runs/{run['id']}/cancel", {})
            raise TimeoutError(f"Replay timed out: {evaluation_id}; cancellation requested")
        time.sleep(3)
        run = retry_safe(gateway, "POST", f"/v1/agent-runs/{run['id']}/sync", {})
    if run["status"] != "done":
        raise ValueError(f"Production agent failed: {evaluation_id}, {run['status']}")
    result = retry_safe(gateway, "POST", f"/v1/workflow-evaluations/{evaluation_id}/grade", {})
    print(transition["name"], "score", result["fields"]["score"], "passed", result["fields"]["passed"], flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["import", "publish-skills", "evaluate"])
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--dataset", default="property-management")
    parser.add_argument("--root", type=Path, default=Path("Property Management"))
    parser.add_argument("--receipt", type=Path, default=Path(".artifacts/workflow-corpus.json"))
    parser.add_argument("--after-step", type=int)
    parser.add_argument("--case-ref")
    parser.add_argument("--split", choices=["training", "holdout"], default="holdout")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=300)
    args = parser.parse_args()
    with Gateway(args.api_url) as gateway:
        if args.command == "import":
            result = import_cases(gateway, args.root, args.dataset, args.receipt)
            return 1 if result["errors"] else 0
        if args.command == "publish-skills":
            publish_skills(gateway, args.dataset, Path("skills"))
            return 0
        cases = gateway.request("GET", "/v1/workflow-cases", query={"dataset": args.dataset, "split": args.split})["items"]
        case_ids = {c["id"] for c in cases if not args.case_ref or c["fields"]["case_ref"] == args.case_ref}
        transitions = gateway.request("GET", "/v1/workflow-transitions", query={"evaluable": True})["items"]
        selected = sorted((t for t in transitions if t["fields"]["case_id"] in case_ids
                           and (args.after_step is None or t["fields"]["after_step"] == args.after_step)),
                          key=lambda t: (t["fields"]["case_id"], t["fields"]["after_step"]))
        if not selected:
            raise ValueError("No controllable transitions match the requested case/split/step")
        if args.limit < 0:
            raise ValueError("Limit must be zero (all) or positive")
        for transition in selected[:args.limit or None]:
            evaluate(gateway, transition, args.timeout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
