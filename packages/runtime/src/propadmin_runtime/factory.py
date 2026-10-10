"""One graph gateway and an ingestion adapter, with a runnable local repository."""

import asyncio
import hmac
import json
from contextlib import asynccontextmanager, suppress

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from propadmin_core import (
    ConflictError,
    GcsStore,
    GraphService,
    IngestionService,
    ProviderNotConfigured,
    RuleService,
    SearchService,
    open_store,
    seed_demo,
)
from propadmin_core.addendum_upgrade import upgrade_addendum
from propadmin_core.ledger import LedgerService
from propadmin_core.provider_directory import ProviderService

from .auth import issue_token, require_internal
from .config import Settings
from .models import Login
from .observability import Telemetry, TelemetryMiddleware

SERVICES = {"api", "ingestion", "rules", "agent", "voice", "email", "browser"}


def create_app(service="api", *, store=None, settings=None, seed=True):
    if service not in SERVICES:
        raise ValueError(f"Unknown service {service!r}")
    cfg = settings or Settings()
    repository = store if store is not None else open_store(cfg.data_path)
    if cfg.mode == "cloud" and store is None and not isinstance(repository, GcsStore):
        raise RuntimeError(
            "Cloud mode needs a shared store: set PROPADMIN_DATA_PATH=gs://bucket/state.json "
            "(or inject a durable SurrealDB repository); local JSON is not a Cloud Run database"
        )
    repository.mutate(upgrade_addendum)

    @asynccontextmanager
    async def lifespan(app):
        # In cloud only the API seeds; a conflict means another instance seeded first.
        if seed and (cfg.mode == "local" or service == "api"):
            try:
                seed_demo(repository)
            except ConflictError:
                pass
        scheduler = None
        if cfg.mode == "local" and service == "api":
            from .ledger_scheduler import start_local_ledger_scheduler

            scheduler = await start_local_ledger_scheduler(app)
        try:
            yield
        finally:
            if scheduler:
                scheduler.cancel()
                with suppress(asyncio.CancelledError):
                    await scheduler
            await asyncio.to_thread(app.state.telemetry.shutdown)

    app = FastAPI(title=f"Properly {service}", version="0.1.0", lifespan=lifespan)
    app.state.telemetry = Telemetry(service)
    app.add_middleware(TelemetryMiddleware, telemetry=app.state.telemetry)
    app.state.settings = cfg
    app.state.store = repository
    app.state.graph = GraphService(repository)
    app.state.ingestion = IngestionService(repository)
    app.state.rules = RuleService(repository)
    app.state.search = SearchService(repository)
    app.state.ledger = LedgerService(repository)
    app.state.providers = ProviderService(repository)

    if service in {"api", "rules"}:
        from .routes_ledger import internal as ledger_internal

        app.include_router(ledger_internal)

    @app.exception_handler(ConflictError)
    async def conflict(request, exc):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(KeyError)
    async def missing(request, exc):
        return JSONResponse(status_code=404, content={"detail": "Record not found"})

    @app.exception_handler(ProviderNotConfigured)
    async def unavailable(request, exc):
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.get("/healthz")
    def health():
        return {"status": "ok", "service": service, "mode": cfg.mode}

    @app.post("/v1/auth/login")
    def login(payload: Login):
        if not hmac.compare_digest(payload.password, cfg.admin_password):
            raise HTTPException(401, "Incorrect password")
        return {"token": issue_token(cfg), "expires_in": 43200}

    @app.get("/v1/auth/status")
    def auth_status():
        return {"required": True, "mode": cfg.mode}

    if service == "api":
        from . import (
            mcp,
            portal_messages,
            portal_sharing,
            portal_stream,
            portal_viewing_rules,
            routes_agent,
            routes_browser,
            routes_email,
            routes_graph,
            routes_ledger,
            routes_ops,
            routes_portal,
            routes_tickets,
            routes_voice,
        )

        for module in (
            routes_graph,
            routes_ledger,
            routes_ops,
            routes_tickets,
            routes_portal,
            portal_messages,
            portal_viewing_rules,
            portal_stream,
            portal_sharing,
            routes_agent,
            routes_voice,
            routes_email,
            routes_browser,
            mcp,
        ):
            app.include_router(module.router)

    if service != "ingestion":
        return app

    internal = APIRouter(prefix="/internal", dependencies=[Depends(require_internal)])

    @internal.post("/events/{stage}")
    async def ingestion_event(stage: str, request: Request):
        payload = await request.json()
        if "message" in payload:
            import base64

            payload = json.loads(base64.b64decode(payload["message"]["data"]))
        if stage not in {"land", "parse", "chunk", "extract", "resolve", "embed", "link"}:
            raise ValueError("Unknown ingestion stage")
        return app.state.ingestion.ingest(payload)

    app.include_router(internal)
    return app
