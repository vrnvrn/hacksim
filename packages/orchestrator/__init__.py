"""HackSim orchestrator. Spawns AXL nodes and Claude Code role workers,
multiplexes their events into a single SSE feed, and serves the web UI.
"""

from .spawner import (
    NodeHandle,
    NodeSpec,
    Spawner,
    SpawnerError,
)
from .sse import (
    Event,
    SseHub,
)

__all__ = [
    "NodeHandle",
    "NodeSpec",
    "Spawner",
    "SpawnerError",
    "Event",
    "SseHub",
]
