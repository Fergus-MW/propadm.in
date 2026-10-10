"""SurrealStore against a real SurrealDB (SURREAL_TEST_URL, root password SURREAL_TEST_PASSWORD)."""

import os
import uuid

import pytest
from propadmin_core.store import ConflictError, publish
from propadmin_core.surreal_store import SurrealStore

URL = os.getenv("SURREAL_TEST_URL")
pytestmark = pytest.mark.skipif(not URL, reason="set SURREAL_TEST_URL to run against SurrealDB")


def stores(count=2):
    db = "t" + uuid.uuid4().hex[:12]
    password = os.getenv("SURREAL_TEST_PASSWORD", "test")
    return [SurrealStore(URL, "test", db, "root", password) for _ in range(count)]


def test_diffs_reach_other_instances_including_deletes_and_events():
    a, b = stores()
    a.mutate(lambda s: s["entities"].update(x={"n": 1, "z": None}, y={"n": 2}))
    assert b.snapshot()["entities"] == {"x": {"n": 1, "z": None}, "y": {"n": 2}}
    assert b.snapshot()["entity_types"]  # defaults persisted by the first write

    def change(state):
        del state["entities"]["x"]
        state["entities"]["y"]["n"] = 3
        state["mcp_sessions"] = {}
        for i in range(2005):
            publish(state, "tick", {"i": i})

    b.mutate(change)
    seen = a.snapshot()
    assert seen["entities"] == {"y": {"n": 3}} and seen["mcp_sessions"] == {}
    assert len(seen["events"]) == 2000 and seen["events"][-1]["payload"] == {"i": 2004}
    assert seen == b.snapshot()


def test_lost_race_reruns_callback_on_winner_state_and_failures_write_nothing():
    a, b = stores()
    a.mutate(lambda s: s.update(version=1))
    b.snapshot()

    def bump(state):
        if state["version"] == 1:  # a's concurrent write lands between b's pull and write
            a.mutate(lambda s: s.update(version=10))
        state["version"] += 1
        return state["version"]

    assert b.mutate(bump) == 11
    assert a.snapshot()["version"] == 11
    with pytest.raises(ValueError):
        a.mutate(lambda s: s["entities"].update(bad=float("nan")))
    with pytest.raises(ConflictError):
        a.mutate(lambda s: (_ for _ in ()).throw(ConflictError("callback failed")))
    assert "bad" not in b.snapshot()["entities"]


def test_import_refuses_non_empty_database():
    (a,) = stores(1)
    a.import_state({"entities": {"e": {"n": 1}}, "events": [], "version": 4})
    assert a.snapshot()["entities"] == {"e": {"n": 1}} and a.snapshot()["version"] == 4
    with pytest.raises(ValueError):
        a.import_state({})
