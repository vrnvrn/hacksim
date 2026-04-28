"""HackSim wire protocol envelopes.

Carried over AXL /send and /recv as UTF-8 encoded JSON. Mirrors the field shape
of the Gensyn autoresearch demo (research_network.py:50-63) so an AXL operator
who understands one understands the other.

Wire shape:

    {
        "proto":     1,
        "type":      "bounty.posted" | "team.forming" | ... ,
        "round":     0..4,                # phase counter
        "sender_id": "<64 hex chars>",    # peer id
        "timestamp": 1714305735.123,      # unix seconds, float
        "payload":   { ... }              # event-specific dict
    }

Envelope encoding is `json.dumps(env).encode("utf-8")`. Decoding is the inverse
followed by structural validation.
"""

from __future__ import annotations

import json
import time
from typing import Any, Final, Literal, TypedDict

PROTO_VERSION: Final[int] = 1


class Phase:
    """Phase counter values carried in the envelope `round` field."""

    BOUNTY_DESIGN: Final[int] = 0
    TEAM_FORMATION: Final[int] = 1
    BUILD: Final[int] = 2
    JUDGING: Final[int] = 3
    SHOWCASE: Final[int] = 4

    ALL: Final[tuple[int, ...]] = (0, 1, 2, 3, 4)


EventType = Literal[
    "bounty.posted",
    "team.forming",
    "team.formed",
    "project.submitted",
    "rubric.published",
    "verdict.published",
    "phase.tick",
    "hackathon.closed",
]


_KNOWN_EVENTS: frozenset[str] = frozenset(
    [
        "bounty.posted",
        "team.forming",
        "team.formed",
        "project.submitted",
        "rubric.published",
        "verdict.published",
        "phase.tick",
        "hackathon.closed",
    ]
)


class Envelope(TypedDict):
    proto: int
    type: EventType
    round: int
    sender_id: str
    timestamp: float
    payload: dict[str, Any]


def is_known_event(t: str) -> bool:
    """Return True if `t` is a known HackSim event type."""
    return t in _KNOWN_EVENTS


def make_envelope(
    *,
    type: EventType,
    round: int,
    sender_id: str,
    payload: dict[str, Any],
    timestamp: float | None = None,
    proto: int = PROTO_VERSION,
) -> Envelope:
    """Construct a well-formed Envelope.

    Validates the event type, the phase, and the sender_id format. Defaults
    timestamp to the current unix time. Does not mutate `payload`.
    """
    if not is_known_event(type):
        raise ValueError(f"unknown event type: {type!r}")
    if round not in Phase.ALL:
        raise ValueError(f"round must be one of {Phase.ALL}, got {round!r}")
    if not isinstance(sender_id, str) or len(sender_id) != 64:
        raise ValueError("sender_id must be a 64-character hex string")
    try:
        int(sender_id, 16)
    except ValueError as e:
        raise ValueError("sender_id must be valid hex") from e
    if not isinstance(payload, dict):
        raise TypeError("payload must be a dict")
    return Envelope(
        proto=proto,
        type=type,
        round=round,
        sender_id=sender_id,
        timestamp=time.time() if timestamp is None else float(timestamp),
        payload=dict(payload),
    )


def encode_envelope(env: Envelope) -> bytes:
    """Serialise an Envelope to UTF-8 JSON bytes ready for POST /send."""
    return json.dumps(env, separators=(",", ":"), sort_keys=False).encode("utf-8")


def decode_envelope(data: bytes) -> Envelope:
    """Parse and validate the bytes from GET /recv into an Envelope.

    Raises ValueError if the bytes are malformed JSON, missing required keys,
    or carry an unknown event type or invalid sender_id.
    """
    try:
        obj = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise ValueError("envelope is not valid UTF-8 JSON") from e
    if not isinstance(obj, dict):
        raise ValueError("envelope must be a JSON object")
    required = {"proto", "type", "round", "sender_id", "timestamp", "payload"}
    missing = required - obj.keys()
    if missing:
        raise ValueError(f"envelope missing required fields: {sorted(missing)}")
    if obj["proto"] != PROTO_VERSION:
        raise ValueError(f"envelope proto version mismatch: got {obj['proto']!r}, want {PROTO_VERSION}")
    return make_envelope(
        type=obj["type"],
        round=int(obj["round"]),
        sender_id=str(obj["sender_id"]),
        payload=obj["payload"] if isinstance(obj["payload"], dict) else {},
        timestamp=float(obj["timestamp"]),
        proto=int(obj["proto"]),
    )
