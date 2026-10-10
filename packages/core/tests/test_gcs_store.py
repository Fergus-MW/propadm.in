"""GcsStore against an in-memory fake bucket: CAS retry, atomicity, cache, cloud gate."""

import pytest
from propadmin_core import ConflictError, GcsStore, open_store
from propadmin_core.store import Store


class PreconditionFailed(Exception):
    code = 412


class FakeBlob:
    def __init__(self, bucket, name, generation=None):
        self.bucket, self.name, self.generation = bucket, name, generation

    def download_as_bytes(self, if_generation_match=None):
        self.bucket.downloads += 1
        if if_generation_match != self.bucket.generation:
            raise PreconditionFailed()
        return self.bucket.data

    def upload_from_string(self, data, content_type=None, if_generation_match=None):
        if self.bucket.race:  # another instance writes first
            self.bucket.race -= 1
            self.bucket.write(self.bucket.data.replace(b'"version": 0', b'"version": 100'))
        if if_generation_match != self.bucket.generation:
            raise PreconditionFailed()
        self.bucket.write(data)
        self.generation = self.bucket.generation


class FakeBucket:
    def __init__(self):
        self.data, self.generation, self.downloads, self.race = None, 0, 0, 0

    def write(self, data):
        self.data, self.generation = data, self.generation + 1

    def get_blob(self, name):
        return FakeBlob(self, name, self.generation) if self.data is not None else None

    def blob(self, name):
        return FakeBlob(self, name)


def bump(state):
    state["version"] += 1
    return state["version"]


def test_cas_retries_callback_after_concurrent_write():
    bucket = FakeBucket()
    store = GcsStore("gs://b/state.json", bucket=bucket)
    store.mutate(lambda state: None)  # initialises the missing object
    assert store.snapshot()["entities"] == {}
    bucket.race = 1
    assert store.mutate(bump) == 101  # re-ran on the concurrent writer's state
    assert store.snapshot()["version"] == 101


def test_exhausted_retries_raise_conflict(monkeypatch):
    monkeypatch.setattr("propadmin_core.gcs_store.time.sleep", lambda _: None)
    bucket = FakeBucket()
    store = GcsStore("gs://b/state.json", bucket=bucket)
    store.mutate(lambda state: None)
    bucket.race = 99
    with pytest.raises(ConflictError):
        store.mutate(bump)


def test_failed_callback_persists_nothing():
    bucket = FakeBucket()
    store = GcsStore("gs://b/state.json", bucket=bucket)
    store.mutate(bump)
    generation = bucket.generation

    def broken(state):
        state["entities"]["x"] = {}
        raise ValueError("boom")

    with pytest.raises(ValueError):
        store.mutate(broken)
    assert bucket.generation == generation
    assert store.snapshot()["entities"] == {}


def test_snapshot_downloads_only_on_generation_change():
    bucket = FakeBucket()
    writer = GcsStore("gs://b/state.json", bucket=bucket)
    reader = GcsStore("gs://b/state.json", bucket=bucket)
    writer.mutate(bump)
    reader.snapshot()
    reader.snapshot()
    assert bucket.downloads == 1
    writer.mutate(bump)
    assert reader.snapshot()["version"] == 2
    assert bucket.downloads == 2


def test_selection_and_cloud_gate(monkeypatch, tmp_path):
    from propadmin_runtime import create_app
    from propadmin_runtime.config import Settings

    # open_store builds GcsStore(path) with no bucket; default it to a fake (no network).
    monkeypatch.setattr("propadmin_core.gcs_store.GcsStore.__init__.__defaults__", (FakeBucket(),))
    assert isinstance(open_store(str(tmp_path / "s.json")), Store)
    cloud = dict(mode="cloud", admin_password="p", token_secret="s", internal_token="i")
    app = create_app(settings=Settings(data_path="gs://b/state.json", **cloud), seed=False)
    assert isinstance(app.state.store, GcsStore)
    with pytest.raises(RuntimeError, match="PROPADMIN_DATA_PATH=surrealdb"):
        create_app(settings=Settings(data_path=str(tmp_path / "s.json"), **cloud))
