"""Idempotent production triplet enrichment for all imported cases through /mcp."""

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .gateway import Gateway


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--dataset", default="property-management")
    parser.add_argument("--case-ref")
    parser.add_argument("--workers", type=int, default=2, choices=[1, 2])
    parser.add_argument("--receipt", type=Path, default=Path(".artifacts/workflow-triplets.json"))
    args = parser.parse_args()
    receipt = {"cases": [], "errors": []}
    with Gateway(args.api_url) as gateway:
        cases = gateway.request("GET", "/v1/workflow-cases", query={"dataset": args.dataset})["items"]
        selected = [c for c in cases if not args.case_ref or c["fields"]["case_ref"] == args.case_ref]

        def enrich(case):
            for attempt in range(3):
                try:
                    return gateway.request("POST", f"/v1/workflow-cases/{case['id']}/triplets", {})
                except Exception as exc:
                    # This endpoint is idempotent. An ambiguous response can safely be retried.
                    if attempt == 2:
                        raise
                    print(case["fields"]["case_ref"], "retry:", str(exc), flush=True)
                    time.sleep(2)

        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(enrich, case): case for case in selected}
            for future in as_completed(futures):
                case = futures[future]
                try:
                    result = future.result()
                    receipt["cases"].append(result)
                    print(case["fields"]["case_ref"], result["triplets"], "triplets",
                          "deduplicated" if result["deduplicated"] else "extracted", flush=True)
                except Exception as exc:
                    receipt["errors"].append({"case_id": case["id"], "error": str(exc)})
                    print(case["fields"]["case_ref"], "FAILED:", str(exc), flush=True)
                args.receipt.parent.mkdir(parents=True, exist_ok=True)
                args.receipt.write_text(json.dumps(receipt, indent=2))
    return int(bool(receipt["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
