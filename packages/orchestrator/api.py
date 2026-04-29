"""FastAPI app exposing the HackSim orchestrator over HTTP.

Endpoints (per UX_SPEC.md section 6):

    POST /api/sim                            create a new simulation
    GET  /api/sim/{sim_id}/snapshot          fetch the current state
    GET  /api/sim/{sim_id}/stream            SSE stream of envelopes
    GET  /api/sim/{sim_id}/projects/{pid}/files          list files
    GET  /api/sim/{sim_id}/projects/{pid}/static/{path}  serve artefact

This commit lands the first three. The project artefact endpoints land in
commit 17 alongside the artefacts module (git-archive on submission, CSP
header on serve).

The app holds an in-memory simulation registry and an SseHub. It does not
yet spawn AXL nodes or Claude Code sessions; that wiring lands in commit
12 once the skill is in place. For now `POST /api/sim` accepts a prompt
and config, allocates a sim id, publishes a `sim.created` event so the
SSE stream proves out, and returns the id.
"""

from __future__ import annotations

import mimetypes
import secrets
from datetime import datetime, timezone
from pathlib import Path as FsPath
from typing import Annotated

from fastapi import FastAPI, HTTPException, Path, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from .artefacts import CSP_HEADER, ArtefactError, ArtefactStore
from .sse import SseHub


class SimConfig(BaseModel):
    builders: int = Field(default=8, ge=1, le=32)
    judges: int = Field(default=3, ge=1, le=10)
    designers: int = Field(default=3, ge=1, le=10)
    duration_hint: str = Field(default="short")


class CreateSimRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)
    config: SimConfig = Field(default_factory=SimConfig)


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
) -> FastAPI:
    """Construct the FastAPI app. The hub and artefact store can be injected for tests."""
    app = FastAPI(title="HackSim Orchestrator", version="0.0.1")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.hub = hub if hub is not None else SseHub()
    app.state.sims = {}
    if artefacts is not None:
        app.state.artefacts = artefacts
    else:
        app.state.artefacts = ArtefactStore(
            base_dir=artefacts_dir or FsPath("sim-runs")
        )

    @app.post("/api/sim", response_model=CreateSimResponse, status_code=status.HTTP_201_CREATED)
    def create_sim(req: CreateSimRequest):
        sim_id = _new_sim_id()
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

    @app.get("/api/sim/{sim_id}/snapshot", response_model=Snapshot)
    def get_snapshot(sim_id: Annotated[str, Path(min_length=1, max_length=64)]):
        record = app.state.sims.get(sim_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"unknown sim id: {sim_id}")
        return record.snapshot()

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

        if sim_id not in app.state.sims and not app.state.hub.has_sim(sim_id):
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
        return JSONResponse({"ok": True, "active_sims": len(app.state.sims)})

    return app


# Module-level app for `uvicorn packages.orchestrator.api:app`
app = create_app()
