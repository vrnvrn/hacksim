"""Skill profile derivation and persona prompt loading."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Final

SKILL_POOL: Final[list[str]] = [
    "Python", "JavaScript", "TypeScript", "Go", "Rust",
    "Solidity", "Cairo", "Move",
    "biology", "chemistry", "finance", "gaming", "ML",
    "viz", "frontend", "backend", "ZK", "smart contracts",
    "networking", "graphics", "audio", "data engineering",
]

PROFILE_SIZE: Final[int] = 3


def skill_profile_for_peer_id(peer_id: str) -> list[str]:
    """Pick a deterministic skill profile for a builder.

    Uses the peer id as the seed so the same builder always has the
    same skills. Profile size is fixed at PROFILE_SIZE; duplicates
    are skipped so we always return a set of distinct skills.
    """
    h = hashlib.sha256(peer_id.encode("ascii")).digest()
    chosen: list[str] = []
    used: set[str] = set()
    i = 0
    while len(chosen) < PROFILE_SIZE and i < len(h):
        idx = h[i] % len(SKILL_POOL)
        skill = SKILL_POOL[idx]
        if skill not in used:
            used.add(skill)
            chosen.append(skill)
        i += 1
    return chosen


def display_name_for_peer_id(peer_id: str) -> str:
    """Return a short, stable display name derived from the peer id.

    Pattern: 'B-' + 4 hex chars. Used in the run log and the UI.
    """
    return f"B-{peer_id[:4]}"


def load_persona_text() -> str:
    md = Path(__file__).resolve().parent / "CLAUDE.md"
    return md.read_text(encoding="utf-8")
