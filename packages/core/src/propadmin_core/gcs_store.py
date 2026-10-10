"""Shared state for Cloud Run: one JSON object in GCS, updated by generation-matched CAS."""

from __future__ import annotations

import copy
import json
import random
import threading
import time

from .store import ConflictError, Store, initial_state, normalise

ATTEMPTS = 8


def _precondition_failed(exc):
    # google.api_core.exceptions.PreconditionFailed carries code 412; duck-typed so the
    # cloud extra stays a lazy import.
    return getattr(exc, "code", None) == 412


class GcsStore:
    """Same interface as Store. A failed callback or lost race never persists partial writes.

    # ponytail: single-object CAS caps throughput at a few writes/sec across all instances
    # and re-uploads the whole state per write; upgrade path is the SurrealDB repository.
    """

    def __init__(self, url, bucket=None):
        bucket_name, _, self.name = url.removeprefix("gs://").partition("/")
        if not bucket_name or not self.name:
            raise ValueError("GCS store path must look like gs://bucket/object.json")
        if bucket is None:
            from google.cloud import storage

            bucket = storage.Client().bucket(bucket_name)
        self.bucket = bucket
        self._lock = threading.RLock()
        self._generation, self._raw, self._state = None, None, None

    def _load(self):
        """Return (generation, raw bytes, state); downloads only when the generation moved."""
        blob = self.bucket.get_blob(self.name)
        if blob is None:
            return 0, None, initial_state()
        if blob.generation != self._generation:
            raw = blob.download_as_bytes(if_generation_match=blob.generation)
            self._generation, self._raw = blob.generation, raw
            self._state = normalise(json.loads(raw))
        return self._generation, self._raw, self._state

    def _retry(self, operation):
        for attempt in range(ATTEMPTS):
            if attempt:
                time.sleep(random.uniform(0, 0.02 * 2**attempt))
            try:
                return operation()
            except Exception as exc:
                if not _precondition_failed(exc):
                    raise
        raise ConflictError("Concurrent updates to shared state; retry the operation")

    def snapshot(self):
        with self._lock:
            return self._retry(lambda: copy.deepcopy(self._load()[2]))

    def mutate(self, callback):
        def attempt():
            generation, raw, current = self._load()
            state = copy.deepcopy(current)
            result = callback(state)
            encoded = json.dumps(state, ensure_ascii=False, allow_nan=False).encode()
            if encoded != raw:  # no-op callbacks (e.g. repeat seeding) skip the write
                blob = self.bucket.blob(self.name)
                blob.upload_from_string(
                    encoded, content_type="application/json", if_generation_match=generation
                )
                self._generation, self._raw, self._state = blob.generation, encoded, state
            return copy.deepcopy(result)

        with self._lock:
            return self._retry(attempt)


def open_store(path=None):
    """`gs://bucket/object` selects the shared GCS store; anything else is local JSON."""
    if str(path or "").startswith("gs://"):
        return GcsStore(path)
    return Store(path)
