"""Deterministic, append-only submission snapshots from observed Cloud Logging evidence.

No model runs here. Missing evidence remains missing; errors never become successful answers.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

from .case_output import clear_conclusion, render_attempt
from .observability import SCHEMA, encode, utcnow


def safe_id(value):
    value = str(value)
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", value):
        raise ValueError("Batch, case and attempt IDs must contain only letters, numbers, _ or -")
    return value


def validate_manifest(manifest):
    safe_id(manifest["batch_id"])
    if manifest.get("kind", "practice") not in {"reality_test", "practice", "dev"}:
        raise ValueError("Manifest kind must be reality_test, practice or dev")
    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("Manifest must contain a non-empty cases list")
    seen, mapping, reverse = set(), {}, {}
    for case in cases:
        key = (safe_id(case["case_id"]), safe_id(case["attempt_id"]))
        if key in seen:
            raise ValueError(f"Duplicate case attempt: {key}")
        folder = safe_id(case.get("organiser_case_id", case["case_id"]))
        if key[0] in mapping and mapping[key[0]] != folder:
            raise ValueError("Case ID mapping must be identical across attempts")
        if folder in reverse and reverse[folder] != key[0]:
            raise ValueError("Different cases cannot map to the same organiser case ID")
        mapping[key[0]], reverse[folder] = folder, key[0]
        seen.add(key)
    return seen


def export_destination(manifest, output=None):
    """Practice is the safe default; only explicit Reality Test batches enter ANSWERS."""
    validate_manifest(manifest)
    reality = manifest.get("kind", "practice") == "reality_test"
    path = (
        Path(output)
        if output is not None
        else (Path("ANSWERS") if reality else Path("evals") / manifest["batch_id"])
    )
    if not reality and any(p.lower() == "answers" for p in (*path.parts, *path.resolve().parts)):
        raise ValueError("Only Reality Test batches (kind=reality_test) may write to ANSWERS")
    if path.exists():
        raise FileExistsError("Output already exists; use a new directory to preserve evidence")
    return path


def resolve_records(entries, artifact_reader=None):
    """Deduplicate delivery, preserve conflicts, and verify every referenced payload."""
    records, by_id, issues = [], {}, defaultdict(list)
    for entry in entries:
        event = entry.get("jsonPayload", entry)
        if not isinstance(event, dict) or event.get("schema") != SCHEMA:
            continue
        event = json.loads(json.dumps(event))
        # Cloud Logging lifts special structured fields out of jsonPayload.
        event.setdefault("timestamp", entry.get("timestamp", ""))
        event.setdefault("severity", entry.get("severity", "DEFAULT"))
        key = (str(event.get("case_id", "")), str(event.get("attempt_id", "")))
        event_id = event.get("event_id")
        if event_id in by_id:
            if by_id[event_id] != event:
                issues[key].append(f"Conflicting duplicate event {event_id}")
                records.append(event)  # retained for inspection, never silently choose a version
            continue
        if not event_id:
            issues[key].append("Event missing event_id")
        by_id[event_id] = event
        records.append(event)
    chunks = defaultdict(dict)
    for event in records:
        if event.get("event") == "payload.chunk":
            payload = event.get("payload", {})
            chunks[payload.get("for_event")][payload.get("index")] = payload.get("data")
    for event in records:
        ref = event.get("payload_ref")
        if not ref:
            continue
        key = (str(event.get("case_id", "")), str(event.get("attempt_id", "")))
        try:
            if "uri" in ref:
                if artifact_reader is None:
                    raise ValueError("GCS artifact reader not configured")
                content = artifact_reader(ref)
            else:
                parts = chunks[ref["event_id"]]
                content = b"".join(
                    base64.b64decode(parts[i], validate=True) for i in range(ref["chunks"])
                )
            if len(content) != ref["bytes"] or hashlib.sha256(content).hexdigest() != ref["sha256"]:
                raise ValueError("Payload length/hash mismatch")
            event["payload"] = json.loads(content)
        except Exception as exc:
            event["evidence_error"] = f"Payload unavailable for {event['event_id']}: {exc}"
            issues[key].append(event["evidence_error"])
    records.sort(key=lambda e: (e.get("timestamp", ""), e.get("event_id", "")))
    return records, issues


def completeness(events, initial_issues=()):
    issues = list(initial_issues)
    if not events:
        return issues + ["No execution evidence was received for this expected case attempt"]
    if not any(e["event"] == "run.created" for e in events):
        issues.append("Missing run.created record")
    if any(e["event"] == "evidence.emit_error" for e in events):
        issues.append("Telemetry could not serialize or deliver part of the execution evidence")
    finished = [e for e in events if e["event"] == "run.finished"]
    if not finished:
        issues.append("No terminal run.finished record; final outcome is unknown")
    runs = {e["run_id"] for e in events if e.get("run_id")}
    for run_id in sorted(runs):
        lifecycle = {e["event"] for e in events if e.get("run_id") == run_id}
        for required in ("run.created", "run.finished"):
            if required not in lifecycle:
                issues.append(f"Missing {required} record for run {run_id}")
    starts = {e["operation_id"] for e in events if e["event"] == "operation.started"}
    ends = {e["operation_id"] for e in events if e["event"] == "operation.finished"}
    issues.extend(f"Unfinished operation {key}" for key in sorted(starts - ends))
    issues.extend(f"Missing start for operation {key}" for key in sorted(ends - starts))
    for terminal in finished:
        payload = terminal.get("payload", {})
        if payload.get("provider_session_id") and not payload.get("provider_events_complete"):
            issues.append("Provider events were not fully collected before this attempt ended")
        if payload.get("status") == "done" and not clear_conclusion(payload.get("final_message")):
            issues.append(
                "No clear final conclusion: closing message sections are missing or empty"
            )
        if "plan" not in payload or "actions" not in payload:
            issues.append("Missing final snapshot of the existing plan/action audit")
        observed_tools = {
            e.get("span_id")
            for e in events
            if e["event"] == "operation.finished"
            and e.get("payload", {}).get("name", "").startswith("execute_tool ")
        }
        issues.extend(
            f"Missing audited tool span {span}"
            for span in sorted(set(payload.get("tool_span_ids", [])) - observed_tools)
        )
        actual = {
            e.get("provider_event_id")
            for e in events
            if e["event"] == "provider.event"
            and e.get("provider_session_id") == payload.get("provider_session_id")
        }
        missing = set(payload.get("provider_event_ids", [])) - actual
        issues.extend(f"Missing provider event {key}" for key in sorted(missing))
    sessions = {e.get("provider_session_id") for e in events if e["event"] == "run.session"}
    snapshots = [e.get("payload", {}) for e in events if e["event"] == "provider.snapshot"]
    for session in sessions:
        if not any(s.get("session_id") == session for s in snapshots):
            issues.append(f"No provider event snapshot for session {session}")
    for snapshot in snapshots:
        actual = {
            e.get("provider_event_id")
            for e in events
            if e["event"] == "provider.event"
            and e.get("provider_session_id") == snapshot.get("session_id")
        }
        issues.extend(
            f"Missing provider event {key}"
            for key in sorted(set(snapshot.get("event_ids", [])) - actual)
        )
    return sorted(set(issues))


def write_json(path, value):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def export_evidence(entries, manifest, output, *, artifact_reader=None, source=None):
    expected = validate_manifest(manifest)
    output = export_destination(manifest, output)
    entries = list(entries)
    records, errors = resolve_records(entries, artifact_reader)
    batch = manifest["batch_id"]
    records = [e for e in records if e.get("batch_id") == batch]
    observed = {(str(e.get("case_id", "")), str(e.get("attempt_id", ""))) for e in records}
    unassigned = observed - expected
    output.mkdir(parents=True, exist_ok=False)  # Never overwrite an earlier execution snapshot.
    report = {
        "schema": SCHEMA,
        "batch_id": batch,
        "kind": manifest.get("kind", "practice"),
        "exported_at": utcnow(),
        "source": source or {"kind": "supplied_records"},
        "cases": {},
        "unexpected_case_attempts": sorted(unassigned),
        "complete": not unassigned,
        "scope": "Checks known case lifecycle, operation pairs, provider event IDs and "
        "payload integrity. Cannot prove events lost before logging or hidden "
        "provider activity. No answers are generated or repaired by this exporter.",
    }
    write_json(output / "manifest.json", manifest)
    with (output / "logs.jsonl").open("x", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(encode(entry).decode() + "\n")
    case_ids = list(dict.fromkeys(str(c["case_id"]) for c in manifest["cases"]))
    for case_id in case_ids:
        attempts = [c for c in manifest["cases"] if str(c["case_id"]) == case_id]
        folder = str(attempts[0].get("organiser_case_id", case_id))
        directory = output / folder
        directory.mkdir()
        case_events = [e for e in records if str(e.get("case_id")) == case_id]
        # A retry must not disappear merely because the supplied manifest is stale.
        attempts += [
            {"case_id": case_id, "attempt_id": attempt, "discovered_in_logs": True}
            for case, attempt in sorted(unassigned)
            if case == case_id
        ]
        receipts = [
            {
                "schema": SCHEMA,
                "event": "runner.receipt",
                "event_id": f"runner-receipt:{batch}:{case_id}:{c['attempt_id']}",
                "source": "batch_runner_receipt",
                "batch_id": batch,
                "case_id": case_id,
                "attempt_id": str(c["attempt_id"]),
                "timestamp": c.get("finished_at"),
                "payload": c,
            }
            for c in attempts
            if c.get("runner_status")
        ]
        with (directory / "trace.jsonl").open("x", encoding="utf-8") as handle:
            for event in case_events + receipts:
                handle.write(encode(event).decode() + "\n")
        answers, reasons, final_results, all_issues = [], [], [], []
        for receipt in attempts:
            attempt = str(receipt["attempt_id"])
            events = [e for e in case_events if str(e.get("attempt_id")) == attempt]
            issues = completeness(events, errors[(case_id, attempt)])
            if receipt.get("discovered_in_logs"):
                issues.append("Attempt absent from supplied manifest; discovered in execution logs")
            answer, reason, final_result = render_attempt(attempt, events, issues, receipt)
            answers.append(answer)
            reasons.append(reason)
            final_results.append(final_result)
            all_issues.extend(f"{attempt}: {issue}" for issue in issues)
        report["cases"][folder] = {
            "case_id": case_id,
            "organiser_case_id": folder,
            "complete": not all_issues,
            "issues": all_issues,
            "event_count": len(case_events) + len(receipts),
        }
        report["complete"] &= not all_issues
        for name, sections in (("ANSWER.md", answers), ("REASONING.md", reasons)):
            with (directory / name).open("x", encoding="utf-8") as handle:
                handle.write(
                    f"# Case {folder}\n\n"
                    + (
                        "## Final result\n\n" + "\n\n---\n\n".join(final_results) + "\n\n"
                        if name == "ANSWER.md"
                        else ""
                    )
                    + "Manifest attempts are retained in order, followed by any unlisted attempts "
                    + "discovered in execution logs; "
                    + "no attempt is silently selected as the successful answer.\n\n"
                    + "\n\n".join(sections)
                    + "\n\nEvidence scope: see ../export.json.\n"
                )
    write_json(output / "export.json", report)
    return report
