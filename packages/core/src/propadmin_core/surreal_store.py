"""Shared state in SurrealDB: one row per record, each write a diff under a global revision.

Same interface as Store. Every instance keeps the whole state in memory and pulls only rows
changed since its cached revision; mutate() sends only the rows its callback changed, in one
transaction that fails if another writer moved the revision first (then it re-runs).
"""

from __future__ import annotations

import base64
import http.client
import json
import os
import pickle
import random
import threading
import time
from urllib.parse import urlsplit

from .store import ConflictError, initial_state, normalise

ROOT, EVENTS = "_root", "_events"
ATTEMPTS = 8
PURGE_LAG = 1000  # tombstones kept this many revisions; readers further behind fully reload
CHUNK = 2_000_000  # bytes per bulk-import transaction

SETUP = """
DEFINE TABLE IF NOT EXISTS store_record SCHEMALESS;
DEFINE INDEX IF NOT EXISTS store_record_rev ON store_record FIELDS rev;
DEFINE TABLE IF NOT EXISTS store_tombstone SCHEMALESS;
DEFINE INDEX IF NOT EXISTS store_tombstone_rev ON store_tombstone FIELDS rev;
DEFINE TABLE IF NOT EXISTS store_meta SCHEMALESS;
"""
PULL = """
BEGIN;
SELECT rev, purged FROM ONLY store_meta:head;
SELECT c, k, v, rev FROM store_record WHERE rev > $since;
SELECT c, k, rev FROM store_tombstone WHERE rev > $since;
COMMIT;
"""
WRITE = """
BEGIN;
LET $head = (SELECT rev, purged FROM ONLY store_meta:head) ?? {rev: 0, purged: 0};
IF $head.rev != $base { THROW "store revision conflict" };
FOR $r IN $rows { UPSERT type::record("store_record", [$r.c, $r.k]) CONTENT $r; };
FOR $r IN $gone {
    DELETE type::record("store_record", [$r.c, $r.k]);
    UPSERT type::record("store_tombstone", [$r.c, $r.k]) CONTENT $r;
};
DELETE store_tombstone WHERE rev <= $purge;
UPSERT store_meta:head CONTENT {rev: $base + 1, purged: math::max([$head.purged, $purge])};
COMMIT;
"""


def clone(value):
    # Same result as deepcopy for JSON-shaped state, ~2.5x faster on the 56 MB prod state.
    return pickle.loads(pickle.dumps(value, pickle.HIGHEST_PROTOCOL))


class SurrealError(RuntimeError):
    pass


class RevisionConflict(ConflictError):
    """Another writer committed first; only this is retried, never a callback's own error."""


def encode(value):
    # Keys and values travel as JSON text: SurrealDB's JSON-RPC otherwise coerces ISO strings
    # to datetimes and `table:id`-shaped strings to (re-escaped) record ids.
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


def flatten(state):
    """{(collection, key): value}; dict roots get a ROOT marker so empty ones survive."""
    rows = {}
    for name, value in state.items():
        if name == "events":
            for event in value:
                rows[(EVENTS, str(event["version"]))] = event
        elif isinstance(value, dict):
            rows[(ROOT, name)] = {}
            for key, item in value.items():
                rows[(name, key)] = item
        else:
            rows[(ROOT, name)] = value
    return rows


def apply(state, events, changes):
    """New state with (rev, c, k, value, gone) changes applied in revision order.

    Copy-on-write: collections are replaced, never edited, so live snapshots stay intact."""
    state, fresh = dict(state), set()
    for _, c, k, value, gone in sorted(changes, key=lambda x: (x[0], x[1] != ROOT)):
        if c == EVENTS:
            events.pop(int(k), None) if gone else events.__setitem__(int(k), value)
        elif c == ROOT:
            state.pop(k, None) if gone else state.__setitem__(k, clone(value))
            fresh.add(k)
        else:
            if c not in fresh:
                state[c], fresh = dict(state.get(c, {})), fresh | {c}
            state[c].pop(k, None) if gone else state[c].__setitem__(k, value)
    state["events"] = [events[v] for v in sorted(events)]
    return normalise(state)


class LazyState(dict):
    """A snapshot whose values are cloned on first access, not all up front.

    The top level wraps each collection in a second LazyState, so touching one record copies
    one record. Untouched values are shared with the store's cache, which is copy-on-write,
    so reads through any path are safe; writes must go through item access (as all code does).
    """

    def __init__(self, source, nest=True):
        super().__init__(source)
        self.touched, self.nest = set(), nest

    def __getitem__(self, key):
        if key not in self.touched and dict.__contains__(self, key):
            value = dict.__getitem__(self, key)
            nested = self.nest and isinstance(value, dict)
            dict.__setitem__(self, key, LazyState(value, False) if nested else clone(value))
            self.touched.add(key)
        return dict.__getitem__(self, key)

    def __reduce_ex__(self, protocol):  # pickle/deepcopy as a plain, fully cloned dict
        return dict, (dict(self.items()),)

    def __setitem__(self, key, value):
        self.touched.add(key)
        dict.__setitem__(self, key, value)

    def get(self, key, default=None):
        return self[key] if key in self else default

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
        return self[key]

    def pop(self, key, *default):
        if key in self:
            self[key]
        return dict.pop(self, key, *default)

    def update(self, *args, **kwargs):
        for key, value in dict(*args, **kwargs).items():
            self[key] = value

    def values(self):
        return [self[key] for key in self]

    def items(self):
        return [(key, self[key]) for key in self]


def diff(current, state):
    """Rows the callback changed: only touched collections, and in them only touched records."""
    changed, removed = {}, set()
    keys = state.touched | (dict.keys(state) ^ current.keys()) if current else set(state)
    for name in keys:
        old = current.get(name)
        new = dict.get(state, name)
        if isinstance(new, LazyState) and isinstance(old, dict):
            for key in new.touched | (dict.keys(new) ^ old.keys()):
                if not dict.__contains__(new, key):
                    removed.add((name, key))
                elif key not in old or old[key] != dict.__getitem__(new, key):
                    changed[(name, key)] = dict.__getitem__(new, key)
            continue
        before = flatten({name: old}) if name in current else {}
        after = flatten({name: dict(new) if isinstance(new, LazyState) else new}) if (
            dict.__contains__(state, name)) else {}
        changed.update((k, v) for k, v in after.items() if k not in before or before[k] != v)
        removed |= before.keys() - after.keys()
    return changed, removed


class SurrealStore:
    """# ponytail: one global revision serialises writers (diffs keep each to milliseconds);
    per-collection revisions are the upgrade path if write contention shows up."""

    def __init__(self, url=None, namespace=None, database=None, user=None, password=None):
        self.url = urlsplit(url or os.getenv("SURREAL_URL", ""))
        if self.url.scheme not in {"http", "https"} or not self.url.hostname:
            raise ValueError("SurrealStore needs SURREAL_URL=http(s)://host:port")
        self.namespace = namespace or os.getenv("SURREAL_NAMESPACE", "propadmin")
        self.database = database or os.getenv("SURREAL_DATABASE", "propadmin")
        login = f"{user or os.getenv('SURREAL_USER', 'root')}:"
        login += password or os.environ["SURREAL_PASSWORD"]
        self._auth = "Basic " + base64.b64encode(login.encode()).decode()
        self._lock = threading.RLock()
        self._conn = None
        self._rev, self._state, self._events = 0, initial_state(), {}
        self._loaded = False
        self.query(
            f"DEFINE NAMESPACE IF NOT EXISTS {self.namespace}; USE NS {self.namespace}; "
            f"DEFINE DATABASE IF NOT EXISTS {self.database}; USE DB {self.database};" + SETUP
        )

    def query(self, sql, variables=None):
        body = json.dumps(
            {"id": 1, "method": "query", "params": [sql, variables or {}]},
            ensure_ascii=False, allow_nan=False,
        ).encode()
        headers = {
            "Authorization": self._auth, "Accept": "application/json",
            "Content-Type": "application/json",
            "Surreal-NS": self.namespace, "Surreal-DB": self.database,
        }
        for retry in (True, False):  # one reconnect for a dropped keep-alive connection
            try:
                if self._conn is None:
                    kind = http.client.HTTPSConnection if self.url.scheme == "https" else (
                        http.client.HTTPConnection)
                    self._conn = kind(self.url.hostname, self.url.port, timeout=60)
                self._conn.request("POST", "/rpc", body, headers)
                response = self._conn.getresponse()
                payload = json.loads(response.read())
                break
            except (OSError, http.client.HTTPException):
                self._conn = None
                if not retry:
                    raise
        if response.status >= 400 or "error" in payload:
            raise SurrealError(f"SurrealDB {response.status}: {str(payload)[:500]}")
        results = payload["result"]
        failed = [r for r in results if r.get("status") != "OK"]
        if failed:
            cause = next((r for r in failed if r.get("kind") != "Query"), failed[0])
            text = str(cause.get("result"))
            if cause.get("kind") == "Thrown" or "conflict" in text.lower():
                raise RevisionConflict(text)
            raise SurrealError(f"SurrealDB rejected a statement: {text[:500]}")
        return [r.get("result") for r in results]

    def _pull(self):
        since = self._rev if self._loaded else 0
        if since:  # point read first: the row scan costs ~5x more and is usually empty
            (head,) = self.query("SELECT rev FROM ONLY store_meta:head;")
            if head and head["rev"] == self._rev:
                return
        _, head, rows, tombstones, _ = self.query(PULL, {"since": since})
        head = head or {"rev": 0, "purged": 0}
        if head["rev"] == self._rev and self._loaded:
            return
        if since and since < head["purged"]:  # missed purged tombstones: reload from scratch
            self._loaded, self._rev = False, 0
            return self._pull()
        if since == 0:
            self._state, self._events = {}, {}
        changes = [(r["rev"], r["c"], json.loads(r["k"]), json.loads(r["v"]), False) for r in rows]
        changes += [(t["rev"], t["c"], json.loads(t["k"]), None, True) for t in tombstones]
        self._state = apply(self._state, self._events, changes)
        if since == 0 and not rows:
            self._state = initial_state()
        self._rev, self._loaded = head["rev"], True

    def _retry(self, operation):
        for attempt in range(ATTEMPTS):
            if attempt:
                time.sleep(random.uniform(0, 0.02 * 2**attempt))
            try:
                return operation()
            except RevisionConflict:
                pass  # the next attempt pulls the winner's rows first
        raise ConflictError("Concurrent updates to shared state; retry the operation")

    def snapshot(self):
        with self._lock:
            self._pull()
            return LazyState(self._state)

    def read(self, fn):
        """fn(state) on the cached state with no up-front copy; fn must not modify it."""
        with self._lock:
            self._pull()
            state = self._state  # copy-on-write: safe to read after releasing the lock
        return clone(fn(state))

    def mutate(self, callback):
        def attempt():
            self._pull()
            current = self._state
            state = LazyState(current)
            result = callback(state)
            changed, removed = diff(current if self._rev else {}, state)
            rev = self._rev + 1
            rows = [{"c": c, "k": encode(k), "rev": rev, "v": encode(v)}
                    for (c, k), v in changed.items()]
            gone = [{"c": c, "k": encode(k), "rev": rev} for (c, k) in removed]
            if rows or gone:
                self.query(WRITE, {"base": self._rev, "rows": rows, "gone": gone,
                                   "purge": rev - PURGE_LAG})
                self._state = normalise({k: dict(v) if isinstance(v, LazyState) else v
                                         for k, v in dict.items(state)})
                self._rev = rev
                self._events = {e["version"]: e for e in self._state["events"]}
            return clone(result)

        with self._lock:
            return self._retry(attempt)

    def import_state(self, state):
        """One-off bulk load into an empty database, in chunked transactions, then the head."""
        with self._lock:
            self._pull()
            if self._rev:
                raise ValueError("SurrealDB store is not empty; refusing to import over it")
            batch, size = [], 0
            for (c, k), v in flatten(normalise(state)).items():
                batch.append({"c": c, "k": encode(k), "rev": 1, "v": encode(v)})
                size += len(batch[-1]["v"])
                if size > CHUNK:
                    self.query('FOR $r IN $rows { UPSERT type::record("store_record", '
                               '[$r.c, $r.k]) CONTENT $r; };', {"rows": batch})
                    batch, size = [], 0
            self.query('FOR $r IN $rows { UPSERT type::record("store_record", [$r.c, $r.k]) '
                       'CONTENT $r; }; UPSERT store_meta:head CONTENT {rev: 1, purged: 0};',
                       {"rows": batch})
            self._loaded = False
            self._pull()
