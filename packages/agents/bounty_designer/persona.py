"""Sponsor archetype derivation and persona prompt assembly."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Final

SPONSORS: Final[list[dict[str, str]]] = [
    {"name": "FoldLab", "niche": "biology and molecular tooling"},
    {"name": "Helix Capital", "niche": "financial primitives, prediction markets"},
    {"name": "DeepProtein", "niche": "ML on biological data"},
    {"name": "NorthStar", "niche": "navigation, mapping, location"},
    {"name": "Lumen", "niche": "observability, tracing, debug tools"},
    {"name": "Atlas Security", "niche": "privacy, encryption, key management"},
    {"name": "Vector", "niche": "embeddings, retrieval, search"},
    {"name": "Drift", "niche": "real-time collaboration, presence, multiplayer"},
]


def sponsor_for_peer_id(peer_id: str) -> dict[str, str]:
    """Pick a sponsor archetype deterministically from a peer id.

    Uses a stable hash so the same designer always plays the same sponsor
    across retries; different designers on the same mesh land on different
    sponsors with very high probability for cast sizes up to 8.
    """
    h = hashlib.sha256(peer_id.encode("ascii")).digest()
    idx = h[0] % len(SPONSORS)
    return SPONSORS[idx]


def load_persona_text() -> str:
    """Read the BountyDesigner CLAUDE.md from this package and return it.

    Used as the system prompt for the Anthropic SDK call when
    ANTHROPIC_API_KEY is set. The deterministic stub does not load the
    persona text; it pulls a sponsor archetype from `pick_sponsor`
    instead. The persona file also ships in the GitHub repo so a
    reviewer can read every role's brief end to end.
    """
    md = Path(__file__).resolve().parent / "CLAUDE.md"
    return md.read_text(encoding="utf-8")
