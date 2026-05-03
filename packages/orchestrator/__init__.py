"""HackSim orchestrator. Spawns AXL nodes and Claude Code role workers,
multiplexes their events into a single SSE feed, and serves the web UI.
"""

from .artefacts import (
    CSP_HEADER,
    ArtefactError,
    ArtefactRecord,
    ArtefactStore,
)
from .controller import SimConfig, SimController
from .log_tailer import LogTailer
from .spawner import (
    NodeHandle,
    NodeSpec,
    RoleHandle,
    Spawner,
    SpawnerError,
)
from .sse import (
    Event,
    SseHub,
)

__all__ = [
    "ArtefactError",
    "ArtefactRecord",
    "ArtefactStore",
    "CSP_HEADER",
    "LogTailer",
    "NodeHandle",
    "NodeSpec",
    "RoleHandle",
    "SimConfig",
    "SimController",
    "Spawner",
    "SpawnerError",
    "Event",
    "SseHub",
]
