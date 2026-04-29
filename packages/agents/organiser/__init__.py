"""Organiser role.

The organiser is the bootstrap node and the choreographer. On startup
it schedules the phase ticks that drive the simulation lifecycle.
During JUDGING it accumulates `verdict.published` envelopes from every
judge. At the end of JUDGING it tallies, ranks the projects, and
broadcasts `hackathon.closed` with the leaderboard.

There is one organiser per simulation. It is the first role spawned
and the last to stop. It does no agent reasoning of its own; the
sim's "voice" comes from designers, builders, and judges.
"""

from .role import run

__all__ = ["run"]
