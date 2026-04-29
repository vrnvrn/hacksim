"""HackSim orchestrator. Spawns AXL nodes and Claude Code role workers,
multiplexes their events into a single SSE feed, and serves the web UI.
"""

from .artefacts import (
    ArtefactError,
    ArtefactRecord,
    ArtefactStore,
    CSP_HEADER,
)
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
    "NodeHandle",
    "NodeSpec",
    "RoleHandle",
    "Spawner",
    "SpawnerError",
    "Event",
    "SseHub",
]
