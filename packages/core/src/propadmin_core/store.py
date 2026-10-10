"""Atomic local repository, with cross-process locks and replayable events."""

from __future__ import annotations

import copy
import fcntl
import json
import os
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

COLLECTIONS = (
    "entities edges documents chunks facts embeddings rules jobs runs plans wakeups "
    "actions changes skills issues proposals credentials claims invocations entity_types "
    "resolutions rule_judgements"
).split()


class ConflictError(ValueError):
    """A concurrent update or conflicting identity invalidated an operation."""


def now():
    return datetime.now(timezone.utc).isoformat()


def identifier(prefix):
    return f"{prefix}:{uuid.uuid4().hex[:16]}"


def initial_state():
    from .registry import default_types

    state = {key: {} for key in COLLECTIONS}
    state.update(version=0, events=[], entity_types=default_types())
    return state


def normalise(state):
    for collection in COLLECTIONS:
        state.setdefault(collection, {})
    state.setdefault("events", [])
    state.setdefault("version", 0)
    return state


def publish(state, kind, payload):
    state["version"] += 1
    event = {
        "version": state["version"],
        "kind": kind,
        "payload": copy.deepcopy(payload),
        "created_at": now(),
    }
    state["events"].append(event)
    state["events"] = state["events"][-2000:]
    return event


class Store:
    """Read-modify-write transactions. A failed callback never persists partial writes."""

    def __init__(self, path=None):
        self.path = Path(path) if path is not None else None
        self._thread_lock = threading.RLock()
        self._state = initial_state()
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _locked(self):
        with self._thread_lock:
            if not self.path:
                yield
                return
            with open(str(self.path) + ".lock", "a+", encoding="utf8") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(lock, fcntl.LOCK_UN)

    def _read(self):
        if self.path and self.path.exists():
            return normalise(json.loads(self.path.read_text(encoding="utf8")))
        return copy.deepcopy(self._state)

    def snapshot(self):
        with self._locked():
            return copy.deepcopy(self._read())

    def mutate(self, callback):
        with self._locked():
            state = self._read()
            result = callback(state)
            # Enforce JSON serialisability before altering the durable state.
            encoded = json.dumps(state, ensure_ascii=False, allow_nan=False)
            if self.path:
                temp = self.path.with_name(f".{self.path.name}.{uuid.uuid4().hex}.tmp")
                try:
                    with temp.open("w", encoding="utf8") as stream:
                        stream.write(encoded)
                        stream.flush()
                        os.fsync(stream.fileno())
                    os.replace(temp, self.path)
                    directory = os.open(self.path.parent, os.O_DIRECTORY)
                    try:
                        os.fsync(directory)
                    finally:
                        os.close(directory)
                finally:
                    temp.unlink(missing_ok=True)
            else:
                self._state = state
            return copy.deepcopy(result)
