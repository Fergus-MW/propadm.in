"""Run an unattended Reality Test batch through the existing API, with a durable receipt."""

import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx
from propadmin_runtime.evidence import export_destination, validate_manifest
from propadmin_runtime.observability import redact, utcnow
from propadmin_runtime.routes_agent import RunCreate


def run_case(client, batch, case, deadline, poll_seconds):
    result = {**case, "started_at": utcnow(), "runner_errors": []}
    run = None

    def request(path, payload=None):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Batch execution deadline reached")
        headers = {
            "x-propadmin-batch-id": batch,
            "x-propadmin-case-id": str(case["case_id"]),
            "x-propadmin-attempt-id": str(case["attempt_id"]),
        }
        response = client.post(
            path, json=payload or {}, headers=headers, timeout=min(30, remaining)
        )
        response.raise_for_status()
        return response.json()

    try:
        # Never automatically retry a create after an ambiguous network failure.
        run = request(
            "/v1/agent-runs",
            {
                "goal": case["goal"],
                "subjects": case.get("subjects", []),
                "case": {
                    "batch_id": batch,
                    "case_id": str(case["case_id"]),
                    "attempt_id": str(case["attempt_id"]),
                    "input": case.get("input", {}),
                },
            },
        )
        result["run_id"] = run["id"]
        while run["status"] in {"queued", "running", "sleeping"}:
            if time.monotonic() >= deadline:
                raise TimeoutError("Batch execution deadline reached")
            time.sleep(min(poll_seconds, max(0, deadline - time.monotonic())))
            try:
                run = request(f"/v1/agent-runs/{run['id']}/sync")
            except httpx.HTTPError as exc:
                result["runner_errors"].append(
                    {"at": utcnow(), "error": str(exc), "action": "retry_sync"}
                )
        result["runner_status"] = run["status"]
    except Exception as exc:
        result["runner_status"] = (
            "deadline_exceeded"
            if isinstance(exc, TimeoutError)
            else ("submission_failed" if run is None else "runner_failed")
        )
        result["runner_errors"].append({"at": utcnow(), "error": str(exc)})
        if run is not None:
            try:
                response = client.post(f"/v1/agent-runs/{run['id']}/cancel", json={}, timeout=10)
                response.raise_for_status()
                result["cancellation"] = "requested"
            except Exception as cancel_error:
                result["runner_errors"].append(
                    {"at": utcnow(), "error": str(cancel_error), "action": "cancel_failed"}
                )
    result["finished_at"] = utcnow()
    return redact(result)


def run_batch(client, manifest, receipt_path, *, parallel=4, deadline_seconds=1500, poll_seconds=5):
    validate_manifest(manifest)
    if not 1 <= parallel <= 20 or deadline_seconds <= 0 or poll_seconds < 0:
        raise ValueError("parallel must be 1..20; deadline positive; poll interval non-negative")
    for case in manifest["cases"]:
        RunCreate.model_validate(
            {
                "goal": case["goal"],
                "subjects": case.get("subjects", []),
                "case": {
                    "batch_id": manifest["batch_id"],
                    "case_id": str(case["case_id"]),
                    "attempt_id": str(case["attempt_id"]),
                    "input": case.get("input", {}),
                },
            }
        )
    receipt_path = export_destination(manifest, receipt_path)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt = {
        "batch_id": manifest["batch_id"],
        "kind": manifest.get("kind", "practice"),
        "started_at": utcnow(),
        "cases": [{**case, "runner_status": "pending"} for case in manifest["cases"]],
    }
    with receipt_path.open("x") as handle:
        json.dump(redact(receipt), handle, indent=2)

    def persist():
        temporary = receipt_path.with_suffix(receipt_path.suffix + ".tmp")
        with temporary.open("w") as handle:
            json.dump(redact(receipt), handle, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(receipt_path)

    deadline = time.monotonic() + deadline_seconds
    with ThreadPoolExecutor(max_workers=parallel) as pool:
        tasks = {
            pool.submit(run_case, client, manifest["batch_id"], case, deadline, poll_seconds): i
            for i, case in enumerate(manifest["cases"])
        }
        for task in as_completed(tasks):
            receipt["cases"][tasks[task]] = task.result()
            persist()
    receipt["finished_at"] = utcnow()
    persist()
    return redact(receipt)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--parallel", type=int, default=4)
    parser.add_argument("--deadline-seconds", type=float, default=1500)
    parser.add_argument(
        "--export-dir", type=Path, help="Optionally export Cloud Logging after execution"
    )
    parser.add_argument("--project", default=os.getenv("GOOGLE_CLOUD_PROJECT"))
    parser.add_argument("--artifact-bucket", default=os.getenv("OBSERVABILITY_ARTIFACT_BUCKET"))
    args = parser.parse_args(argv)
    token = os.getenv("PROPADMIN_ADMIN_TOKEN")
    if not token:
        parser.error("Set PROPADMIN_ADMIN_TOKEN to an existing API admin token")
    if args.export_dir and (not args.project or args.export_dir.exists()):
        parser.error("Auto-export needs --project and a new --export-dir")
    try:
        manifest = json.loads(args.manifest.read_text())
        if args.export_dir:
            export_destination(manifest, args.export_dir)
        with httpx.Client(
            base_url=args.api_url.rstrip("/"), headers={"Authorization": f"Bearer {token}"}
        ) as client:
            receipt = run_batch(
                client,
                manifest,
                args.receipt,
                parallel=args.parallel,
                deadline_seconds=args.deadline_seconds,
            )
        print(f"Processed {len(receipt['cases'])} cases; receipt: {args.receipt}")
        if args.export_dir:
            from infra.scripts.export_evidence import main as export_main

            options = [
                "--project",
                args.project,
                "--manifest",
                str(args.receipt),
                "--since",
                receipt["started_at"],
                "--until",
                receipt["finished_at"],
                "--out",
                str(args.export_dir),
            ]
            if args.artifact_bucket:
                options += ["--artifact-bucket", args.artifact_bucket]
            export_status = export_main(options)
            return export_status or (
                0 if all(c["runner_status"] == "done" for c in receipt["cases"]) else 2
            )
    except Exception as exc:
        parser.exit(1, f"Batch command failed: {type(exc).__name__}: {redact(str(exc))}\n")
    return 0 if all(c["runner_status"] == "done" for c in receipt["cases"]) else 2


if __name__ == "__main__":
    raise SystemExit(main())
