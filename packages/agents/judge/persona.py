"""Judge archetype derivation and rubric weight assignment."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Final


CRITERIA: Final[list[str]] = [
    "novelty",
    "technical_depth",
    "demo_quality",
    "documentation",
    "bounty_fit",
]


# Each archetype has a name plus a weight tuple aligned to CRITERIA.
ARCHETYPES: Final[list[dict]] = [
    {
        "name": "encouraging",
        "weights": (0.20, 0.15, 0.30, 0.15, 0.20),
        "tone_hint": "leads with what worked",
    },
    {
        "name": "balanced",
        "weights": (0.20, 0.20, 0.20, 0.20, 0.20),
        "tone_hint": "even-handed",
    },
    {
        "name": "strict",
        "weights": (0.25, 0.30, 0.10, 0.20, 0.15),
        "tone_hint": "demands engineering depth",
    },
    {
        "name": "contrarian",
        "weights": (0.30, 0.15, 0.15, 0.10, 0.30),
        "tone_hint": "rewards strange angles",
    },
]


def archetype_for_peer_id(peer_id: str) -> dict:
    """Pick a judge archetype deterministically from a peer id."""
    h = hashlib.sha256(peer_id.encode("ascii")).digest()
    idx = h[0] % len(ARCHETYPES)
    return ARCHETYPES[idx]


def display_name_for_peer_id(peer_id: str) -> str:
    return f"J-{peer_id[:4]}"


def load_persona_text() -> str:
    md = Path(__file__).resolve().parent / "CLAUDE.md"
    return md.read_text(encoding="utf-8")
