"""Move shared state from the GCS JSON object into SurrealDB (SURREAL_* env, e.g. via IAP tunnel).

  import  gs://bucket/state.json   bulk-load into an empty SurrealDB; saves the baseline locally
  catchup gs://bucket/state.json   after the cutover, replay writes old revisions made to GCS
"""

import json
import sys
from pathlib import Path

from google.cloud import storage
from propadmin_core.store import normalise
from propadmin_core.surreal_store import SurrealStore, flatten

BASELINE = Path(".data/migration-baseline.json")


def download(url):
    bucket, _, name = url.removeprefix("gs://").partition("/")
    blob = storage.Client().bucket(bucket).get_blob(name)
    return blob.generation, normalise(json.loads(blob.download_as_bytes()))


def main(command, url):
    generation, state = download(url)
    store = SurrealStore()
    if command == "import":
        BASELINE.parent.mkdir(exist_ok=True)
        BASELINE.write_text(json.dumps({"generation": generation, "state": state}))
        store.import_state(state)
        assert store.snapshot() == state, "SurrealDB copy differs from the GCS state"
        print(f"Imported generation {generation}; baseline saved to {BASELINE}")
        return
    baseline = json.loads(BASELINE.read_text())
    before, after = flatten(baseline["state"]), flatten(state)
    # Records only: the event tail and its counter belong to whichever store is live now.
    def record(key):
        return key[0] != "_events" and key != ("_root", "version")

    changed = {k: v for k, v in after.items() if record(k) and before.get(k, ...) != v}
    gone = {k for k in before.keys() - after.keys() if record(k)}

    def replay(target):
        rows = flatten(target)
        rows.update(changed)
        for key in gone:
            rows.pop(key, None)
        target.clear()
        for (c, k), value in rows.items():
            if c == "_root":
                target.setdefault(k, value)
            elif c == "_events":
                target.setdefault("events", []).append(value)
            else:
                target.setdefault(c, {})[k] = value
        target["events"].sort(key=lambda event: event["version"])

    store.mutate(replay)
    print(f"Replayed {len(changed)} changed and {len(gone)} removed records written to GCS "
          f"between generation {baseline['generation']} and {generation}")


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in {"import", "catchup"}:
        sys.exit(__doc__)
    main(*sys.argv[1:])
