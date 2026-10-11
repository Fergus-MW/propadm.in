"""Live portal connections receive the durable version before subsequent updates."""

import asyncio
import json
from types import SimpleNamespace

from propadmin_core import Store
from propadmin_runtime.portal_stream import stream


def test_portal_stream_emits_current_version():
    store = Store()

    async def connected():
        return False

    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(store=store)),
        is_disconnected=connected,
    )

    async def receive():
        response = await stream(request)
        message = await anext(response.body_iterator)
        await response.body_iterator.aclose()
        return message

    event = asyncio.run(receive())
    assert 'event: delta' in event
    data = next(line.removeprefix('data: ') for line in event.splitlines() if line.startswith('data: '))
    assert json.loads(data) == {'version': store.snapshot()['version']}
