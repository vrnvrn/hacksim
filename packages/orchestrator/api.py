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
from .recorder import read_recording
from .snapshot import apply_events, empty_snapshot
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
    """Mint a fresh sim id with date prefix and an 8-hex random suffix.

    8 hex characters give us 4 billion ids; birthday-collision risk
    drops to roughly 1-in-65k after 65k sims (vs 1-in-4k after 4k
    sims with the older 6-char suffix). Worst case for a single
    submission is still negligible, but the wider space is free.
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"sim_{today}_{secrets.token_hex(4)}"


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
            # one stops every prior controller so their AXL nodes release the
            # bootstrap port (127.0.0.1:9100) and clear the loopback
            # Yggdrasil mesh of stale peers. Without this, the new sim's
            # designers reach the old organiser, peer with builders that are
            # gone, and bounty.posted broadcasts go to the empty old mesh.
            # The new sim's own builders never hear bounties.
            #
            # Stops run concurrently via stop_fast (SIGKILL based) so the
            # POST returns within ~2.5 seconds. Earlier this code fired the
            # stops as background tasks for fast response, but that left the
            # AXL nodes alive on shared ports while the new spawn started,
            # which is the same race the new logic prevents.
            prior = list(app.state.controllers.values())
            app.state.controllers.clear()

            async def _stop_one_fast(c):
                try:
                    c.hub.close(c.sim_id)
                except Exception:
                    pass
                try:
                    await asyncio.wait_for(c.stop_fast(), timeout=2.5)
                except (asyncio.TimeoutError, Exception):
                    pass

            if prior:
                await asyncio.gather(
                    *(_stop_one_fast(c) for c in prior),
                    return_exceptions=True,
                )

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
                    # `req.config` is a Pydantic SimConfig with no secret
                    # fields. The Anthropic key lives on CreateSimRequest
                    # itself (with Field(exclude=True) plus SecretStr) and
                    # never reaches this dict because we serialise
                    # req.config in isolation, not the full request.
                    "config": req.config.model_dump(),
                    "created_at": controller.snapshot["created_at"],
                    "llm": "anthropic" if user_key else "stub",
                },
            )
            # Kick off start() in the background so the HTTP response
            # returns the sim id quickly. The default population spawns
            # 15 nodes (1 organiser + 3 designers + 8 builders + 3 judges)
            # and that takes ~10s on a clean loopback.
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

    @app.delete("/api/sim/{sim_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def stop_sim(sim_id: Annotated[str, Path(min_length=1, max_length=64)]):
        """Stop a running simulation (auto-start mode only).

        Calls SimController.stop, closes the SSE channel for this sim id,
        and removes the controller from app state. Subsequent
        snapshot/stream requests with the same id return 404. Useful when
        a user wants to free the loopback ports without spawning a new
        sim, and as a cleanup hook for the future "stop this sim" UI.
        """
        controller: SimController | None = app.state.controllers.pop(sim_id, None)
        if controller is None:
            # Not auto-start mode, or the sim was never running.
            if app.state.sims.pop(sim_id, None) is None:
                raise HTTPException(status_code=404, detail=f"unknown sim id: {sim_id}")
            return None
        try:
            controller.hub.close(sim_id)
        except Exception:
            pass
        try:
            await controller.stop()
        except Exception:
            pass
        return None

    @app.post("/api/sim/reset", status_code=status.HTTP_204_NO_CONTENT)
    async def reset_sims():
        """Stop every running sim and free the loopback bootstrap port.

        Idempotent. Safe to call from any state. Used by the in-UI
        Restart button on /sim/<id>: a wedged sim (designer workers
        crashed, AXL nodes stuck) is recoverable from the browser
        without dropping to a terminal.

        Stops run concurrently via SimController.stop_fast (SIGKILL
        based), each capped at 2.5 seconds. Returns 204 on success.
        """
        prior = list(app.state.controllers.values())
        app.state.controllers.clear()

        async def _stop_one_fast(c):
            try:
                c.hub.close(c.sim_id)
            except Exception:
                pass
            try:
                await asyncio.wait_for(c.stop_fast(), timeout=2.5)
            except (asyncio.TimeoutError, Exception):
                pass

        if prior:
            await asyncio.gather(
                *(_stop_one_fast(c) for c in prior),
                return_exceptions=True,
            )
        return None

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

    # ------------------------------------------------------------------ replay

    def _replay_path(run_id: str) -> FsPath:
        """Resolve a recording path under base_dir, refusing path-escape."""
        if not run_id or "/" in run_id or ".." in run_id:
            raise HTTPException(status_code=404, detail="unknown recording")
        base = FsPath(app.state.base_dir)
        candidate = base / run_id / "events.jsonl"
        try:
            resolved = candidate.resolve()
            base_resolved = base.resolve()
            if not str(resolved).startswith(str(base_resolved) + os.sep) and resolved != base_resolved:
                raise HTTPException(status_code=404, detail="unknown recording")
        except (OSError, RuntimeError):
            raise HTTPException(status_code=404, detail="unknown recording") from None
        return candidate

    @app.get("/api/replay")
    def list_replays():
        """List every recording on disk under base_dir.

        Each entry carries `run_id`, `prompt`, `started_at`, `events`,
        and `duration_s` so the frontend can render a small picker
        without parsing every line of every recording. Reading the meta
        line plus the file size is enough to populate the list cheaply.

        Directories without an `events.jsonl` are silently skipped. This
        covers two real cases: half-spawned sims that crashed before any
        event was published, and pre-recorder sim directories left over
        from before commit 66 added the Recorder. See
        `test_skips_pre_recorder_sim_directories` for the regression.
        """
        base = FsPath(app.state.base_dir)
        entries: list[dict] = []
        if not base.exists():
            return {"replays": entries}
        for child in sorted(base.iterdir()):
            events_file = child / "events.jsonl"
            if not events_file.is_file():
                continue
            try:
                meta, evs = read_recording(events_file)
            except (FileNotFoundError, ValueError):
                continue
            duration = round(evs[-1]["t"], 2) if evs else 0.0
            entries.append(
                {
                    "run_id": child.name,
                    "prompt": meta.get("prompt", ""),
                    "started_at": meta.get("started_at", ""),
                    "events": len(evs),
                    "duration_s": duration,
                }
            )
        return {"replays": entries}

    @app.get("/api/replay/{run_id}/snapshot")
    def replay_snapshot(run_id: Annotated[str, Path(min_length=1, max_length=64)]):
        """Return the final snapshot accumulated from a recorded run.

        Same shape as `/api/sim/<id>/snapshot` so the frontend can swap
        endpoints without other changes. Useful as the initial-state
        fetch before subscribing to `/api/replay/<id>/stream`.
        """
        path = _replay_path(run_id)
        try:
            meta, events = read_recording(path)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="unknown recording") from None
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

        snap = empty_snapshot(
            sim_id=meta.get("sim_id", run_id),
            prompt=meta.get("prompt", ""),
            config=meta.get("config", {}),
            created_at=meta.get("started_at", ""),
        )
        snap = apply_events(snap, [(e["type"], e["data"]) for e in events])
        return snap

    @app.get("/api/replay/{run_id}/stream")
    async def replay_stream(
        run_id: Annotated[str, Path(min_length=1, max_length=64)],
        request: Request,
        speed: Annotated[float, Query(ge=0.1, le=100.0)] = 4.0,
    ):
        """Stream a recorded run as SSE, honouring the original timing.

        `speed` defaults to 4x so a five-minute run finishes in ~75
        seconds. Set `speed=1` for original cadence; `speed=0.1` for a
        slow walk; the upper bound of 100x effectively flushes the
        whole recording without sleeping.
        """
        path = _replay_path(run_id)
        try:
            meta, events = read_recording(path)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="unknown recording") from None
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

        async def gen():
            # Open with a synthetic sim.created so the client UI sees a
            # familiar lead-in even if the original recording started
            # mid-sim. The frontend already tolerates duplicate
            # sim.created events (apply_event clamps the snapshot to the
            # same shape).
            from .sse import Event as SseEvent

            seq = 1
            yield SseEvent(
                seq=seq,
                type="replay.started",
                data={
                    "run_id": run_id,
                    "speed": speed,
                    "events_total": len(events),
                    "duration_s": round(events[-1]["t"], 2) if events else 0.0,
                    "prompt": meta.get("prompt", ""),
                },
                sim_id=run_id,
            ).to_sse_bytes()
            seq += 1

            last_t = 0.0
            for evt in events:
                if await request.is_disconnected():
                    return
                target = evt["t"]
                delay = max(0.0, (target - last_t) / max(speed, 0.001))
                # Clamp very long inter-event gaps so a quiet phase does
                # not stall the replay for the viewer.
                if delay > 5.0:
                    delay = 5.0
                if delay > 0:
                    await asyncio.sleep(delay)
                last_t = target
                yield SseEvent(
                    seq=seq,
                    type=str(evt["type"]),
                    data=dict(evt["data"]),
                    sim_id=run_id,
                ).to_sse_bytes()
                seq += 1

            # One terminal event so the frontend knows the recording
            # finished cleanly (vs the connection dropping).
            yield SseEvent(
                seq=seq,
                type="replay.finished",
                data={"run_id": run_id, "events_total": len(events)},
                sim_id=run_id,
            ).to_sse_bytes()

        return StreamingResponse(
            gen(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
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
