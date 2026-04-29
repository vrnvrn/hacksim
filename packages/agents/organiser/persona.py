"""Organiser persona constants.

The organiser does not have archetypes; one per sim. We export the
phase schedule defaults here so tests and the choreography can
share them.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from packages.protocol import Phase


# Default "quick" pace per CLAUDE.md. Configurable later via SimConfig.
DEFAULT_SCHEDULE: Final[list[tuple[float, int]]] = [
    (5.0, Phase.BOUNTY_DESIGN),
    (18.0, Phase.TEAM_FORMATION),
    (30.0, Phase.BUILD),
    (75.0, Phase.JUDGING),
]
DEFAULT_CLOSE_AT: Final[float] = 110.0


PACE_PRESETS: Final[dict[str, dict[str, float]]] = {
    "smoke": {
        # Used by scripts/smoke_e2e.py to keep the test run under 90 seconds.
        # Not exposed in the production UI dial.
        "bounty_design_at": 4.0,
        "team_formation_at": 16.0,
        "build_at": 26.0,
        "judging_at": 50.0,
        "close_at": 75.0,
    },
    "quick": {
        "bounty_design_at": 5.0,
        "team_formation_at": 18.0,
        "build_at": 30.0,
        "judging_at": 75.0,
        "close_at": 110.0,
    },
    "medium": {
        "bounty_design_at": 10.0,
        "team_formation_at": 40.0,
        "build_at": 70.0,
        "judging_at": 240.0,
        "close_at": 340.0,
    },
    "deep": {
        "bounty_design_at": 20.0,
        "team_formation_at": 80.0,
        "build_at": 140.0,
        "judging_at": 540.0,
        "close_at": 720.0,
    },
}


def load_persona_text() -> str:
    md = Path(__file__).resolve().parent / "CLAUDE.md"
    return md.read_text(encoding="utf-8")
