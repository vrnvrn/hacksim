"""SimController: owns the lifecycle of one running simulation.

A SimController combines:

- a `Spawner` that brings up the AXL node binaries and the role worker
  Python processes,
- one `LogTailer` per role that publishes worker stdout to the SseHub
  and folds events through the snapshot accumulator,
- the live `snapshot` dict the FastAPI app serves on
  `GET /api/sim/{id}/snapshot`,
- start and stop lifecycle hooks.

Spawning is async so the FastAPI POST /api/sim handler can return the
sim id quickly while the AXL nodes come up in the background.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from packages.agents.builder.persona import (
    display_name_for_peer_id as builder_display_name,
    skill_profile_for_peer_id,
)

from .artefacts import ArtefactStore
from .log_tailer import LogTailer
from .snapshot import apply_event, empty_snapshot
from .spawner import NodeSpec, Spawner
from .sse import SseHub


@dataclass
class SimConfig:
    builders: int = 8
    judges: int = 3
    designers: int = 3
    duration_hint: str = "short"
    pace: str = "quick"  # smoke, quick, medium, deep


class SimController:
    """Owns one running HackSim simulation.

    Construct, then `await controller.start()`, then `await controller.stop()`.
    Live snapshot at `controller.snapshot`. Events flow through the hub for
    SSE subscribers and through `apply_event` to mutate the snapshot.
    """

    def __init__(
        self,
        *,
        sim_id: str,
        prompt: str,
        config: SimConfig,
        hub: SseHub,
        base_dir: Path,
        axl_bin: Path,
        orch_url: str | None = None,
        artefacts: ArtefactStore | None = None,
        spawner: Spawner | None = None,
        extra_env: dict[str, str] | None = None,
    ):
        self.sim_id = sim_id
        self.prompt = prompt
        self.config = config
        self.hub = hub
        self.base_dir = base_dir
        self.axl_bin = axl_bin
        self.orch_url = orch_url
        self.artefacts = artefacts
        # Per-sim secrets (currently the user-supplied ANTHROPIC_API_KEY)
        # land in worker env via the spawner's extra_env hook. Never logged,
        # never published to the hub, never written to disk.
        self._extra_env: dict[str, str] = dict(extra_env or {})
        self._snapshot: dict = empty_snapshot(
            sim_id=sim_id,
            prompt=prompt,
            config=_config_to_dict(config),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._spawner = spawner or Spawner(
            base_dir=base_dir,
            axl_bin=axl_bin,
            sim_id=sim_id,
            orch_url=orch_url,
        )
        self._tailers: list[LogTailer] = []
        self._running = False

    @property
    def snapshot(self) -> dict:
        return self._snapshot

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def role_count(self) -> int:
        return len(self._spawner.role_handles)

    # ------------------------------------------------------------------ start

    async def start(self) -> None:
        """Spawn the role population, attach a tailer per role, seed the
        builder roster on the snapshot. Idempotent: a second call is a no-op.
        """
        if self._running:
            return
        self._running = True

        # Pace forwards to the organiser and any other role that reads it.
        # Direct assignment, not setdefault, so a second sim in the same
        # process picks up its own pace instead of inheriting the first
        # sim's value.
        os.environ["HACKSIM_PACE"] = self.config.pace

        # Publish an axl.binary event before any spawn fires. Captures
        # the binary path, size, and mtime so the run log shows which
        # build is in play. Useful when a stale build silently changes
        # behaviour after a submodule update.
        self._publish_axl_binary_health()

        # 1) Bootstrap organiser.
        loop = asyncio.get_event_loop()
        organiser = await loop.run_in_executor(
            None,
            lambda: self._spawner.spawn_role(
                role="organiser",
                index=0,
                is_bootstrap=True,
                extra_env=self._extra_env or None,
            ),
        )
        self._attach_tailer(organiser, role="organiser")

        # 2) Designers, builders, judges.
        designers = []
        for i in range(self.config.designers):
            handle = await loop.run_in_executor(
                None,
                lambda i=i: self._spawner.spawn_role(
                    role="bounty_designer",
                    index=i,
                    extra_env=self._extra_env or None,
                ),
            )
            self._attach_tailer(handle, role="bounty_designer")
            designers.append(handle)

        builders = []
        for i in range(self.config.builders):
            handle = await loop.run_in_executor(
                None,
                lambda i=i: self._spawner.spawn_role(
                    role="builder",
                    index=i,
                    extra_env=self._extra_env or None,
                ),
            )
            self._attach_tailer(handle, role="builder")
            builders.append(handle)

        judges = []
        for i in range(self.config.judges):
            handle = await loop.run_in_executor(
                None,
                lambda i=i: self._spawner.spawn_role(
                    role="judge",
                    index=i,
                    extra_env=self._extra_env or None,
                ),
            )
            self._attach_tailer(handle, role="judge")
            judges.append(handle)

        # 3) Seed the builder roster on the snapshot. Each builder's peer id is
        # known to its AXL node at this point; we query /topology and emit a
        # `builder.registered` envelope into the hub. The accumulator picks it
        # up and the live page renders builder chips immediately.
        for handle in builders:
            try:
                pk = await loop.run_in_executor(None, _query_peer_id, handle.api_url)
            except Exception:
                pk = ""
            if not pk:
                continue
            payload = {
                "peer_id": pk,
                "display_name": builder_display_name(pk),
                "skills": list(skill_profile_for_peer_id(pk)),
            }
            self._publish("builder.registered", payload)

        # 4) Sim-level housekeeping event so the SSE stream announces the
        # configured population.
        self._publish(
            "sim.spawned",
            {
                "sim_id": self.sim_id,
                "organiser": 1,
                "designers": len(designers),
                "builders": len(builders),
                "judges": len(judges),
            },
        )

    # -------------------------------------------------------------------- stop

    async def stop(self) -> None:
        """Stop tailers (drain remaining lines), then nodes."""
        if not self._running:
            return
        for tailer in self._tailers:
            try:
                await tailer.stop(drain=True)
            except Exception:
                pass
        self._tailers.clear()
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._spawner.stop_all)
        self._running = False

    # ---------------------------------------------------------------- internals

    def _attach_tailer(self, handle, *, role: str) -> None:
        tailer = LogTailer(
            sim_id=self.sim_id,
            log_path=handle.worker_log_path,
            hub=self.hub,
            role=role,
            listener=self._on_event,
        )
        self._tailers.append(tailer)
        # Schedule on the event loop; do not await so we keep spawning.
        asyncio.create_task(tailer.start())

    def _on_event(self, event_type: str, payload: dict[str, Any]) -> None:
        self._snapshot = apply_event(self._snapshot, event_type, payload)

    def _publish(self, event_type: str, payload: dict[str, Any]) -> None:
        """Publish to the hub and fold into the snapshot in one step.

        Used for SimController-originated events (builder.registered,
        sim.spawned) that do not flow through a worker log.
        """
        try:
            self.hub.publish(self.sim_id, event_type, payload)
        except Exception:
            pass
        self._on_event(event_type, payload)

    def _publish_axl_binary_health(self) -> None:
        """Emit an axl.binary event capturing path, size, and mtime so the
        run log shows which build is in play. AXL itself does not expose a
        --version flag (verified against third_party/axl/cmd/node/main.go),
        so we surface the on-disk metadata as the closest proxy.
        """
        axl_path = self._spawner.axl_bin
        try:
            stat = axl_path.stat()
            payload = {
                "path": str(axl_path),
                "size_bytes": stat.st_size,
                "mtime": stat.st_mtime,
                "executable": True,
            }
        except FileNotFoundError:
            payload = {
                "path": str(axl_path),
                "size_bytes": 0,
                "mtime": 0,
                "executable": False,
                "error": "binary not found at the configured path",
            }
        try:
            self.hub.publish(self.sim_id, "axl.binary", payload)
        except Exception:
            pass


# ---------------------------------------------------------------------- helpers


def _config_to_dict(cfg: SimConfig) -> dict:
    return {
        "builders": cfg.builders,
        "judges": cfg.judges,
        "designers": cfg.designers,
        "duration_hint": cfg.duration_hint,
        "pace": cfg.pace,
    }


def _query_peer_id(api_url: str) -> str:
    """Synchronously query an AXL node's /topology for its public key."""
    import json
    import urllib.request

    with urllib.request.urlopen(f"{api_url}/topology", timeout=5.0) as r:
        body = r.read().decode("utf-8")
    obj = json.loads(body)
    return str(obj.get("our_public_key", ""))
