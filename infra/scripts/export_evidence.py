"""Export a bounded Cloud Logging batch into immutable ANSWERS/<case>/ evidence files."""

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from propadmin_runtime.evidence import (
    completeness,
    export_destination,
    export_evidence,
    resolve_records,
    validate_manifest,
)
from propadmin_runtime.observability import SCHEMA


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timestamps must include a timezone (use Z for UTC)")
    return parsed.astimezone(timezone.utc).isoformat()


def read_entries(client, batch_id, since, until):
    # JSON quoting prevents filter injection. The client iterator follows every page,
    # including pages with no entries and a nextPageToken; no max_results truncation.
    query = (
        f"jsonPayload.schema={json.dumps(SCHEMA)} "
        f"AND jsonPayload.batch_id={json.dumps(batch_id)} "
        f"AND timestamp>={json.dumps(since)} AND timestamp<={json.dumps(until)}"
    )
    return [
        entry.to_api_repr()
        for entry in client.list_entries(filter_=query, order_by="timestamp asc", page_size=1000)
    ]


def supporting_logs(client, project, records, since, until):
    """Include native request/container logs correlated with observed trace IDs."""
    traces = {e.get("trace_id") for e in records}
    traces.update(
        e.get("payload", {}).get("input", {}).get("request_trace_id")
        for e in records
        if e.get("event") == "operation.started"
    )
    traces = sorted(value for value in traces if value)
    entries = []
    for offset in range(0, len(traces), 40):
        clauses = [
            f"trace={json.dumps(f'projects/{project}/traces/{value}')}"
            for value in traces[offset : offset + 40]
        ]
        query = (
            f"({' OR '.join(clauses)}) AND timestamp>={json.dumps(since)} "
            f"AND timestamp<={json.dumps(until)}"
        )
        entries.extend(
            entry.to_api_repr()
            for entry in client.list_entries(
                filter_=query, order_by="timestamp asc", page_size=1000
            )
        )
    return entries


class ArtifactReader:
    def __init__(self, bucket):
        self.bucket, self.client, self.cache = bucket, None, {}

    def __call__(self, ref):
        if not self.bucket or not ref["uri"].startswith(f"gs://{self.bucket}/evidence/"):
            raise ValueError("Artifact is outside the configured --artifact-bucket")
        key = (ref["uri"], ref["generation"])
        if key not in self.cache:
            if self.client is None:
                from google.cloud import storage

                self.client = storage.Client()
            name = ref["uri"].removeprefix(f"gs://{self.bucket}/")
            blob = self.client.bucket(self.bucket).blob(name, generation=int(ref["generation"]))
            self.cache[key] = blob.download_as_bytes(
                if_generation_match=int(ref["generation"]), timeout=30
            )
        return self.cache[key]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=os.getenv("GOOGLE_CLOUD_PROJECT"))
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--since", required=True, help="UTC start, e.g. 2026-10-10T15:25:00Z")
    parser.add_argument("--until", required=True, help="Fixed execution cutoff, including timezone")
    parser.add_argument(
        "--out", type=Path, help="Default: ANSWERS for reality_test; evals/<batch> otherwise"
    )
    parser.add_argument("--artifact-bucket", default=os.getenv("OBSERVABILITY_ARTIFACT_BUCKET"))
    parser.add_argument(
        "--wait-seconds",
        type=float,
        default=30,
        help="Wait for late-arriving logs; execution cutoff stays fixed",
    )
    args = parser.parse_args(argv)
    if not args.project:
        parser.error("--project or GOOGLE_CLOUD_PROJECT is required")
    if not 0 <= args.wait_seconds <= 300:
        parser.error("--wait-seconds must be between 0 and 300")
    try:
        since, until = timestamp(args.since), timestamp(args.until)
        if since >= until:
            raise ValueError("--since must precede --until")
        manifest = json.loads(args.manifest.read_text())
        expected = validate_manifest(manifest)
        args.out = export_destination(manifest, args.out)
        from google.cloud import logging_v2

        client = logging_v2.Client(project=args.project)  # Application Default Credentials
        reader = ArtifactReader(args.artifact_bucket)
        deadline = time.monotonic() + args.wait_seconds
        while True:
            entries = read_entries(client, manifest["batch_id"], since, until)
            records, issues = resolve_records(entries, reader)
            complete = all(
                not completeness(
                    [
                        e
                        for e in records
                        if (str(e.get("case_id")), str(e.get("attempt_id"))) == key
                    ],
                    issues[key],
                )
                for key in expected
            )
            if complete or time.monotonic() >= deadline:
                break
            time.sleep(min(5, max(0, deadline - time.monotonic())))
        extra = supporting_logs(client, args.project, records, since, until)
        # Supporting queries also return our evidence. Keep one copy of each raw LogEntry.
        unique = {json.dumps(entry, sort_keys=True): entry for entry in entries + extra}
        report = export_evidence(
            list(unique.values()),
            manifest,
            args.out,
            artifact_reader=reader,
            source={
                "kind": "cloud_logging",
                "project": args.project,
                "since": since,
                "until": until,
            },
        )
    except Exception as exc:
        parser.exit(1, f"Evidence export failed: {type(exc).__name__}: {exc}\n")
    print(
        f"Exported {len(report['cases'])} cases to {args.out}; "
        f"evidence {'checks passed' if report['complete'] else 'INCOMPLETE — see export.json'}"
    )
    return 0 if report["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
