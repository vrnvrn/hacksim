"""FastAPI app exposing the HackSim orchestrator over HTTP.

Endpoints (per UX_SPEC.md section 6):

    POST /api/sim                            create a new simulation
    GET  /api/sim/{sim_id}/snapshot          fetch the current state
    GET  /api/sim/{sim_id}/stream            SSE stream of envelopes
    POST /api/sim/{sim_id}/projects                      register an artefact
    GET  /api/sim/{sim_id}/projects/{pid}/files          list files
    GET  /api/sim/{sim_id}/projects/{pid}/static/{path}  serve artefact

`POST /api/sim` starts a real SimController by default (commit 28): it
spawns the AXL nodes plus the role workers, attaches log tailers, and
returns the sim id while the population finishes coming up in the
background. `GET /api/sim/{id}/snapshot` returns the live snapshot the
controller maintains.

For tests and offline mocks, callers pass `auto_start=False` to
`create_app`; in that mode the endpoint behaves as before, allocating a
sim id and publishing `sim.created` without spawning anything.
"""

from __future__ import annotations

import asyncio
import mimetypes
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path as FsPath
from typing import Annotated

from fastapi import FastAPI, HTTPException, Path, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, SecretStr

from .artefacts import CSP_HEADER, ArtefactError, ArtefactStore
from .controller import SimConfig as ControllerConfig
from .controller import SimController
from .sse import SseHub


_LOCAL_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})


def _is_localhost_request(request: Request) -> bool:
    """True when the request originates from this machine.

    The user-supplied Anthropic key field on POST /api/sim is gated on
    this. The frontend dev server proxies to the orchestrator on
    localhost; the user's browser hits the frontend on localhost too. A
    deployed instance of the orchestrator behind a public proxy gets
    real client IPs through `X-Forwarded-For`; when that header is
    present we trust it (the proxy terminates the TCP, so client.host
    is the proxy itself).
    """
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        return first in _LOCAL_HOSTS
    client_host = request.client.host if request.client else None
    if client_host in _LOCAL_HOSTS:
        return True
    # Starlette's TestClient sets client.host="testclient". It only
    # appears in unit tests, never on a real socket, so treat it as
    # local for testing the localhost-only key path.
    return client_host == "testclient"


class SimConfig(BaseModel):
    # Hard upper bounds on a single-laptop loopback Yggdrasil mesh. Above
    # these the recv queue (bounded at 100 per node) saturates and
    # bounty.posted gossip stops propagating reliably. Pick numbers that
    # produce a watchable demo, not a realistic conference.
    builders: int = Field(default=8, ge=1, le=10)
    judges: int = Field(default=3, ge=1, le=5)
    designers: int = Field(default=3, ge=1, le=5)
    duration_hint: str = Field(default="short")
    pace: str = Field(default="quick")


class CreateSimRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)
    config: SimConfig = Field(default_factory=SimConfig)
    # Optional, local-only. Pydantic SecretStr keeps the value out of repr,
    # model_dump, and any logger that prints model fields. The endpoint
    # rejects this field when the request did not originate from localhost.
    anthropic_api_key: SecretStr | None = Field(default=None, exclude=True)


class CreateSimResponse(BaseModel):
    id: str
    stream_url: str


class Snapshot(BaseModel):
    """Initial-state snapshot per UX_SPEC.md section 7. Empty until commits
    13+ start populating bounties, builders, projects, judges, verdicts."""

    id: str
    prompt: str
    config: SimConfig
    phase: int = 0
    created_at: str
    bounties: list = []
    builders: list = []
    teams: list = []
    projects: list = []
    judges: list = []
    verdicts: list = []


class _SimRecord:
    """In-memory record of one running simulation."""

    def __init__(self, sim_id: str, prompt: str, config: SimConfig):
        self.id = sim_id
        self.prompt = prompt
        self.config = config
        self.phase = 0
        self.created_at = datetime.now(timezone.utc).isoformat()

    def snapshot(self) -> Snapshot:
        return Snapshot(
            id=self.id,
            prompt=self.prompt,
            config=self.config,
            phase=self.phase,
            created_at=self.created_at,
        )


def _new_sim_id() -> str:
    """Stable-prefixed id of the form sim_YYYY-MM-DD_xxxxxx."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"sim_{today}_{secrets.token_hex(3)}"


def create_app(
    *,
    hub: SseHub | None = None,
    artefacts: ArtefactStore | None = None,
    artefacts_dir: FsPath | None = None,
    auto_start: bool | None = None,
    base_dir: FsPath | None = None,
    axl_bin: FsPath | None = None,
    orch_url: str | None = None,
) -> FastAPI:
    """Construct the FastAPI app. The hub and artefact store can be injected for tests.

    When `auto_start=True` (the default in production), `POST /api/sim`
    boots a real SimController. When `auto_start=False`, the endpoint
    behaves as before (record only, no spawn) so unit tests stay fast.

    `base_dir` is where each sim stores its working trees; `axl_bin` is
    the path to the AXL Go binary; `orch_url` is the URL the role workers
    use to POST artefact registrations back to the orchestrator.
    """
    app = FastAPI(title="HackSim Orchestrator", version="0.0.1")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.hub = hub if hub is not None else SseHub()
    app.state.sims = {}  # legacy in-memory records (auto_start=False)
    app.state.controllers = {}  # sim_id -> SimController (auto_start=True)
    if artefacts is not None:
        app.state.artefacts = artefacts
    else:
        app.state.artefacts = ArtefactStore(
            base_dir=artefacts_dir or FsPath("sim-runs")
        )

    if auto_start is None:
        auto_start = os.environ.get("HACKSIM_AUTO_START", "false").lower() in {"1", "true", "yes"}
    app.state.auto_start = auto_start
    app.state.base_dir = base_dir or FsPath(os.environ.get("HACKSIM_RUNS_DIR", "sim-runs"))
    app.state.axl_bin = axl_bin or FsPath(os.environ.get("HACKSIM_AXL_BIN", "third_party/axl/node"))
    app.state.orch_url = orch_url or os.environ.get("HACKSIM_ORCH_URL", "http://127.0.0.1:8000")

    @app.post("/api/sim", response_model=CreateSimResponse, status_code=status.HTTP_201_CREATED)
    async def create_sim(req: CreateSimRequest, request: Request):
        sim_id = _new_sim_id()

        # Local-only gate on the Anthropic key. A hosted deployment must not
        # accept user-pasted keys: a public paste box is a credential
        # harvesting vector. The user is told to set the env var on the
        # host instead.
        user_key: str | None = None
        if req.anthropic_api_key is not None:
            if not _is_localhost_request(request):
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "anthropic_api_key is only accepted on localhost. "
                        "Set it as an env var on the host instead."
                    ),
                )
            user_key = req.anthropic_api_key.get_secret_value()

        if app.state.auto_start:
            # The orchestrator runs one simulation at a time. Booting a fresh
            # one stops every prior controller so their AXL nodes do not
            # saturate the loopback Yggdrasil mesh and starve the new sim's
            # bounty.posted broadcasts. Wait for the prior shutdowns to
            # finish before spawning the new controller; otherwise two
            # rapid spin-up clicks race and the old AXL binaries fight the
            # new ones for ports.
            prior = list(app.state.controllers.values())
            app.state.controllers.clear()

            async def _stop_one(c):
                try:
                    await c.stop()
                except Exception:
                    pass

            for old in prior:
                try:
                    old.hub.close(old.sim_id)
                except Exception:
                    pass
            if prior:
                await asyncio.gather(*(_stop_one(o) for o in prior))

            cfg = ControllerConfig(
                builders=req.config.builders,
                judges=req.config.judges,
                designers=req.config.designers,
                duration_hint=req.config.duration_hint,
                pace=req.config.pace,
            )
            controller = SimController(
                sim_id=sim_id,
                prompt=req.prompt,
                config=cfg,
                hub=app.state.hub,
                base_dir=FsPath(app.state.base_dir) / sim_id,
                axl_bin=FsPath(app.state.axl_bin),
                orch_url=app.state.orch_url,
                artefacts=app.state.artefacts,
                # Per-sim env overlay. The key never lands in the snapshot,
                # the SSE buffer, or any log payload because it is not a
                # field of `cfg`. It only travels into spawned worker
                # process envs from here.
                extra_env={"ANTHROPIC_API_KEY": user_key} if user_key else None,
            )
            app.state.controllers[sim_id] = controller
            app.state.hub.publish(
                sim_id,
                "sim.created",
                {
                    "sim_id": sim_id,
                    "prompt": req.prompt,
                    # `req.config` is a Pydantic SimConfig; model_dump excludes
                    # the SecretStr key field thanks to `exclude=True`. Even
                    # so we are explicit so a future field rename never
                    # accidentally leaks the key.
                    "config": req.config.model_dump(exclude={"anthropic_api_key"}),
                    "created_at": controller.snapshot["created_at"],
                    "llm": "anthropic" if user_key else "stub",
                },
            )
            # Kick off start() in the background so the HTTP response
            # returns the sim id quickly. Spawning 11 nodes can take ~10s.
            asyncio.create_task(_safe_start(controller, app))
            return CreateSimResponse(id=sim_id, stream_url=f"/api/sim/{sim_id}/stream")

        record = _SimRecord(sim_id=sim_id, prompt=req.prompt, config=req.config)
        app.state.sims[sim_id] = record
        app.state.hub.publish(
            sim_id,
            "sim.created",
            {
                "sim_id": sim_id,
                "prompt": req.prompt,
                "config": req.config.model_dump(),
                "created_at": record.created_at,
            },
        )
        return CreateSimResponse(id=sim_id, stream_url=f"/api/sim/{sim_id}/stream")

    @app.get("/api/sim/{sim_id}/snapshot")
    def get_snapshot(sim_id: Annotated[str, Path(min_length=1, max_length=64)]):
        controller: SimController | None = app.state.controllers.get(sim_id)
        if controller is not None:
            return controller.snapshot
        record = app.state.sims.get(sim_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"unknown sim id: {sim_id}")
        return record.snapshot().model_dump()

    @app.on_event("shutdown")
    async def _on_shutdown():
        # Cleanly stop every running controller so workers and AXL nodes
        # do not leak when the orchestrator restarts.
        for controller in list(app.state.controllers.values()):
            try:
                await controller.stop()
            except Exception:
                pass
        app.state.controllers.clear()

    @app.get("/api/sim/{sim_id}/stream")
    async def stream_events(
        sim_id: Annotated[str, Path(min_length=1, max_length=64)],
        request: Request,
        last_event_id: Annotated[int | None, Query(alias="last_event_id")] = None,
    ):
        # Honour the Last-Event-ID header if the query param is not set.
        if last_event_id is None:
            header = request.headers.get("last-event-id")
            if header is not None:
                try:
                    last_event_id = int(header)
                except ValueError:
                    last_event_id = None

        if (
            sim_id not in app.state.sims
            and sim_id not in app.state.controllers
            and not app.state.hub.has_sim(sim_id)
        ):
            raise HTTPException(status_code=404, detail=f"unknown sim id: {sim_id}")

        hub: SseHub = app.state.hub

        async def event_generator():
            async for evt in hub.subscribe(sim_id, last_event_id=last_event_id):
                if await request.is_disconnected():
                    return
                yield evt.to_sse_bytes()

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
        )

    @app.post("/api/sim/{sim_id}/projects", status_code=201)
    def register_project(
        sim_id: Annotated[str, Path(min_length=1, max_length=64)],
        payload: dict,
    ):
        """Role workers POST here after broadcasting project.submitted.

        The orchestrator git-archives the working tree at the commit
        hash into sim-runs/{sim_id}/projects/{project_id}/, then publishes
        a project.submitted event onto the SSE stream so the frontend
        learns about the new artefact.
        """
        store: ArtefactStore = app.state.artefacts
        try:
            record = store.register(sim_id, payload)
        except ArtefactError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

        files = record.files()
        app.state.hub.publish(
            sim_id,
            "project.submitted",
            {
                "project_id": record.project_id,
                "title": record.title,
                "tagline": record.tagline,
                "commit_hash": record.commit_hash,
                "entry_path": record.entry_path,
                "files_count": len(files),
                "team_id": payload.get("team_id"),
                "bounty_id": payload.get("bounty_id"),
            },
        )
        return {
            "project_id": record.project_id,
            "files": files,
            "entry_path": record.entry_path,
            "commit_hash": record.commit_hash,
        }

    @app.get("/api/sim/{sim_id}/projects/{pid}/files")
    def list_project_files(
        sim_id: Annotated[str, Path(min_length=1, max_length=64)],
        pid: Annotated[str, Path(min_length=1, max_length=64)],
    ):
        store: ArtefactStore = app.state.artefacts
        record = store.get(sim_id, pid)
        if record is None:
            raise HTTPException(status_code=404, detail="unknown project")
        return {
            "project_id": record.project_id,
            "commit_hash": record.commit_hash,
            "entry_path": record.entry_path,
            "github_url": None,
            "title": record.title,
            "tagline": record.tagline,
            "files": record.files(),
        }

    @app.get("/api/sim/{sim_id}/projects/{pid}/files/{rel:path}")
    def read_project_file(
        sim_id: Annotated[str, Path(min_length=1, max_length=64)],
        pid: Annotated[str, Path(min_length=1, max_length=64)],
        rel: str,
    ):
        store: ArtefactStore = app.state.artefacts
        path = store.safe_path(sim_id, pid, rel)
        if path is None or not path.exists() or not path.is_file():
            raise HTTPException(status_code=404, detail="file not found")
        media_type, _ = mimetypes.guess_type(path.name)
        return FileResponse(
            path=str(path),
            media_type=media_type or "application/octet-stream",
        )

    @app.get("/api/sim/{sim_id}/projects/{pid}/static/{rel:path}")
    def serve_static(
        sim_id: Annotated[str, Path(min_length=1, max_length=64)],
        pid: Annotated[str, Path(min_length=1, max_length=64)],
        rel: str,
    ):
        """Static-file route used by the iframe modal.

        Strict CSP makes the agent code safe to embed: no network calls,
        no plugins, no top-level navigation, scripts and styles only from
        the same origin or inline. The frontend pairs this with
        sandbox=\"allow-scripts\" on the iframe element.
        """
        store: ArtefactStore = app.state.artefacts
        path = store.safe_path(sim_id, pid, rel)
        if path is None or not path.exists() or not path.is_file():
            raise HTTPException(status_code=404, detail="file not found")
        media_type, _ = mimetypes.guess_type(path.name)
        return FileResponse(
            path=str(path),
            media_type=media_type or "application/octet-stream",
            headers={
                "Content-Security-Policy": CSP_HEADER,
                "Cache-Control": "private, max-age=60",
                "X-Content-Type-Options": "nosniff",
            },
        )

    @app.get("/api/health")
    def health():
        return JSONResponse(
            {
                "ok": True,
                "auto_start": app.state.auto_start,
                "active_sims": len(app.state.sims) + len(app.state.controllers),
            }
        )

    return app


async def _safe_start(controller: SimController, app: FastAPI) -> None:
    """Run controller.start in the background, publishing a structured
    error event if anything goes wrong so the SSE stream surfaces it."""
    try:
        await controller.start()
    except Exception as e:
        app.state.hub.publish(
            controller.sim_id,
            "sim.start_error",
            {"error": str(e)},
        )


# Module-level app for `uvicorn packages.orchestrator.api:app`
app = create_app()
