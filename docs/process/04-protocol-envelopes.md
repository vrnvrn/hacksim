# 04. Wire protocol envelopes

## What changed

- New module `packages/protocol/` with `envelopes.py` and `__init__.py`.
- `Envelope` TypedDict matching the wire shape from PLAN.md section 5.
- `Phase` constant class with the five phase values (BOUNTY_DESIGN through SHOWCASE).
- `EventType` Literal with the eight HackSim event types.
- `make_envelope()` constructor with full validation (event type, phase, sender_id format).
- `encode_envelope()` and `decode_envelope()` for the JSON-on-the-wire format.
- `is_known_event()` predicate.
- 32-test suite at `packages/protocol/tests/test_envelopes.py` covering construction, validation, encoding, decoding, error paths, phase constants, and three specific envelope shapes from the spec.

## Why

The protocol module is the single source of truth for what the wire looks like. Every other package (`axl_client`, `agents/*`, `orchestrator`) imports from here. Defining it before the transport means the transport tests can use real envelopes from day one, and the agents do not have to invent their own message shapes. This is the same lego principle as the autoresearch demo's `research_network.py`, where one file owns the wire and every agent uses it.

The validation in `make_envelope()` is deliberately strict. A 64-character hex sender_id is the AXL peer id format, not arbitrary text. A round value outside `Phase.ALL` is a programming error, not a wire fault. Catching these at construction time keeps the run log tidy and the tests sharp.

The encoding uses `separators=(",", ":")` for compact JSON, identical to what `research_network.py` produces. Decoding verifies the proto version matches `PROTO_VERSION = 1`; future protocol changes bump the constant and require a coordinated rollout.

## How to verify

```
.venv/bin/python -m pytest packages/protocol/tests/ -v
```

Expected: 32 tests pass in under a second.

Inspect a sample envelope on the wire:

```python
from packages.protocol import make_envelope, encode_envelope, Phase
env = make_envelope(
    type="bounty.posted",
    round=Phase.BOUNTY_DESIGN,
    sender_id="a" * 64,
    payload={"title": "FoldLab"},
)
print(encode_envelope(env))
# b'{"proto":1,"type":"bounty.posted","round":0,"sender_id":"aaaa...","timestamp":...,"payload":{"title":"FoldLab"}}'
```

## Gensyn surface used

Mirrors the Envelope shape in `collaborative-autoresearch-demo/skills/autoresearch-network/research_network.py:50-63`. Same fields (`proto`, `round`, `sender_id`, `timestamp`), same encoding (`json.dumps(env).encode("utf-8")`), same posting pattern. Different `type` values: theirs is fixed to `"finding"`, ours is the eight-value HackSim vocabulary so consumers can route on type without sniffing the payload.

## Up next

Commit 05 introduces the urllib-based AxlClient at `packages/axl_client/client.py`. It calls `GET /topology`, `POST /send`, and `GET /recv` against the local AXL node, with a fake httpd in the tests so the unit ring stays AXL-free. Commit 06 layers on the peer enumeration logic from `research_network.py:214-234`.
