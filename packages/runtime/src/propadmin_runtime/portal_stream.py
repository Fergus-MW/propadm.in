"""Small version stream: clients refetch canonical projections after durable writes."""

import asyncio
import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from .auth import require_admin

router = APIRouter(prefix="/v1/portal", dependencies=[Depends(require_admin)])


@router.get("/stream")
async def stream(request: Request):
    async def events():
        version = None
        while not await request.is_disconnected():
            current = (await asyncio.to_thread(request.app.state.store.snapshot))["version"]
            if current != version:
                version = current
                yield f"id: {version}\nevent: delta\ndata: {json.dumps({'version': version})}\n\n"
            else:
                yield ": heartbeat\n\n"
            await asyncio.sleep(2)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )
