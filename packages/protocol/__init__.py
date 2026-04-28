"""HackSim wire protocol. JSON envelopes carried over AXL /send and /recv.

The Envelope shape mirrors the autoresearch demo's protocol from
research_network.py:50-63. We preserve the proto/round/sender_id/timestamp
fields, retype `type` to the HackSim event vocabulary, and move event-specific
fields into a single `payload` dict so consumers can validate per type.
"""

from .envelopes import (
    PROTO_VERSION,
    Phase,
    EventType,
    Envelope,
    make_envelope,
    encode_envelope,
    decode_envelope,
    is_known_event,
)

__all__ = [
    "PROTO_VERSION",
    "Phase",
    "EventType",
    "Envelope",
    "make_envelope",
    "encode_envelope",
    "decode_envelope",
    "is_known_event",
]
