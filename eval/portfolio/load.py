"""Import through the real API and validated graph service into isolated stores."""

import copy
import json
import os
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from .check import inside, read_pack, verify_state
from .io import fresh_directory, read_json, write_json


def load(pack, platform_root, destination, *, mode="sharded", selected=None, save_state=False):
    root, platform = Path(pack).resolve(), Path(platform_root).resolve()
    manifest, indexes = read_pack(root)
    if not (platform / "packages/runtime/src").is_dir():
        raise ValueError("Select the platform checkout with --platform-root")
    for relative in ("packages/core/src", "packages/runtime/src"):
        sys.path.insert(0, str(platform / relative))
    import httpx
    from fastapi.testclient import TestClient
    from propadmin_core import Store
    from propadmin_runtime import create_app
    from propadmin_runtime.config import Settings

    out = fresh_directory(destination)
    directory, groups = indexes[0], indexes[1:]
    selected = set(selected or [])
    available = {group["sources"][0]["shard"] for group in groups}
    if selected - available:
        raise ValueError(f"Unknown properties: {selected - available}")
    groups = [g for g in groups if not selected or g["sources"][0]["shard"] in selected]
    expected = {ref: read_json(root / "evaluator-only" / f"{ref}.json") for ref in available}
    if mode == "combined":
        batches = [("portfolio", [directory, *groups], [expected[g["sources"][0]["shard"]] for g in groups])]
    else:
        batches = [("directory", [directory], [])]
        for group in groups:
            row = expected[group["sources"][0]["shard"]]
            providers = {repair["provider_id"] for repair in row["repairs"]}
            chosen = [s for s in directory["sources"] if s["path"].endswith("/agency.json") or
                      any(r.get("id") in providers for r in json.loads(inside(root, s["path"]).read_text()))]
            paths = {s["path"] for s in chosen}
            subset = {"sources": chosen, "relationships": [r for r in directory["relationships"] if r["evidence_source"] in paths]}
            batches.append((row["property_ref"], [subset, group], [row]))
    results = []
    env = {"EXTRACTION_PROVIDER": "local", "EMBEDDING_PROVIDER": "local"}
    with patch.dict(os.environ, env), \
         patch.object(httpx.HTTPTransport, "handle_request", side_effect=RuntimeError("External HTTP disabled")), \
         patch.object(httpx.AsyncHTTPTransport, "handle_async_request", side_effect=RuntimeError("External HTTP disabled")):
        for label, batch, oracle in batches:
            started = time.monotonic()
            row = {"batch": label, "status": "error", "source_count": 0}
            store = Store()
            app = create_app("api", store=store, seed=False, settings=Settings(mode="local", admin_password="portfolio-only",
                token_secret="portfolio-only", internal_token="portfolio-only"))
            client = TestClient(app)  # No lifespan: no demo seed or wall-clock rent scheduler.
            try:
                login = client.post("/v1/auth/login", json={"password": "portfolio-only"})
                login.raise_for_status()
                client.headers["Authorization"] = "Bearer " + login.json()["token"]
                documents = {}
                all_sources = [s for group in batch for s in group["sources"]]
                for source in all_sources:
                    payload = {**source["upload"], "text": inside(root, source["path"]).read_text()}
                    response = client.post("/v1/ingest/upload", json=payload)
                    if response.status_code != 201:
                        raise ValueError(f"{source['path']}: {response.status_code} {response.text[:1000]}")
                    job = response.json()
                    if job["status"] != "completed":
                        raise ValueError(f"Incomplete source: {source['path']}")
                    documents[source["path"]] = job["document_id"]
                    row["source_count"] += 1
                for group in batch:
                    for relation in group["relationships"]:
                        payload = {k: copy.deepcopy(relation[k]) for k in ("source", "target", "relation", "attributes")}
                        payload["evidence"] = [{"document_id": documents[relation["evidence_source"]]}]
                        app.state.graph.link_entities(payload, actor="synthetic-portfolio-import",
                                                      reason="Supplied CRM relationship: " + relation["evidence_source"])
                before = store.snapshot()
                # Replay representative identity, email and money sources in each shard.
                replays = [s for s in all_sources if s["path"].endswith(("/crm.json", "/bank.csv", "/intake.eml"))]
                if not replays:
                    replays = all_sources[:1]
                for source in replays:
                    response = client.post("/v1/ingest/upload", json={**source["upload"], "text": inside(root, source["path"]).read_text()})
                    response.raise_for_status()
                    if not response.json().get("deduplicated") or response.json()["document_id"] != documents[source["path"]]:
                        raise ValueError(f"Duplicate import was not idempotent: {source['path']}")
                state = store.snapshot()
                if state != before:
                    raise ValueError("Duplicate source replay changed graph or ledger state")
                errors = verify_state(state, oracle)
                if errors:
                    raise ValueError("; ".join(errors[:12]))
                for source in all_sources:
                    doc = state["documents"][documents[source["path"]]]
                    if doc["text"] != inside(root, source["path"]).read_text() or not doc["chunks"]:
                        raise ValueError("Source evidence did not survive ingestion")
                if save_state:
                    # Save the actual platform snapshot, without rewriting domain state.
                    path = out / label / "state.json"
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(json.dumps(state, separators=(",", ":")), encoding="utf-8")
                    restored = Store(path).snapshot()
                    if restored != state:
                        raise ValueError("Snapshot did not survive local Store reload")
                write_json(out / label / "document-map.json", documents)
                row.update(status="passed", entities=dict(Counter(e["type"] for e in state["entities"].values())),
                           documents=len(state["documents"]), edges=len(state["edges"]), replayed_sources=len(replays),
                           unallocated=len(state.get("unallocated", {})))
            except Exception as error:
                row["error"] = f"{type(error).__name__}: {error}"
            finally:
                client.close()
            row["seconds"] = round(time.monotonic() - started, 3)
            results.append(row)
            print(json.dumps(row), flush=True)
            write_json(out / "progress.json", results)
    report = {"kind": "portfolio_ingestion_validation", "mode": mode,
              "platform_revision": subprocess.check_output(["git", "-C", str(platform), "rev-parse", "HEAD"], text=True).strip(),
              "pack_sources_sha256": manifest["sources_sha256"], "real_agent_executed": False,
              "real_provider_calls": False, "selected_properties": len(groups), "batches": results,
              "passed": sum(r["status"] == "passed" for r in results), "errors": sum(r["status"] == "error" for r in results),
              "limitations": "Offline extraction; sharded mode does not establish whole-portfolio load performance or cross-shard identity behaviour."}
    write_json(out / "results.json", report)
    return report
