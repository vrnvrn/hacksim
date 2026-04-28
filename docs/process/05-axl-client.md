# 05. AxlClient with topology, send, recv

## What changed

- New module `packages/axl_client/` with `client.py` defining `AxlClient`, three dataclasses (`Topology`, `PeerInfo`, `ReceivedMessage`), and an `AxlError` exception type.
- `AxlClient.get_topology()` decodes the JSON from `GET /topology` into a `Topology` dataclass, tolerating missing fields and skipping malformed peer entries.
- `AxlClient.send(peer_id, data, content_type)` posts to `POST /send` with the `X-Destination-Peer-Id` header, returns the byte count from `X-Sent-Bytes`.
- `AxlClient.recv()` polls `GET /recv` and returns one `ReceivedMessage` or `None` when the AXL queue signals 204.
- Pure stdlib (`urllib.request`, `urllib.error`). No third-party HTTP dependency.
- Test infrastructure at `packages/axl_client/tests/_fake_axl.py`: a `ThreadingHTTPServer`-based fake AXL node built only from `http.server`. Captures every `/send` call and lets tests inject `/recv` responses.
- 15 tests in `packages/axl_client/tests/test_client.py` covering constructor, topology decoding (happy path, missing fields, malformed entries, error status), send (headers, content type, bytes/bytearray/memoryview, type error, error status), recv (empty queue, ordered drain, error status), and one end-to-end shape test that round-trips a real `Envelope` through the fake.

## Why

The autoresearch demo uses pure urllib for the same reason: zero install footprint, no concerns about which HTTP library version a downstream agent is using. Matching that policy keeps HackSim deployable in the same conditions as Gensyn's flagship demo.

The fake AXL is a tiny `ThreadingHTTPServer` that starts on an ephemeral port. It is not a full AXL replica; it captures the contract our client depends on (the three endpoints, the headers, the 204 sentinel). The integration test in commit 07 boots two real AXL binaries to exercise the layers below this contract.

The `Topology` dataclass models the upstream JSON exactly. We tolerate missing `up`, missing `peers`, missing `tree`. The decoder skips entries that are not dicts or that lack a `public_key`. This matches the defensive shape of `research_network.py:214-234` (which uses `.get(...)` everywhere with sensible defaults).

`AxlError` carries the HTTP status and the raw body so callers can build helpful error messages. Most callers just let the error propagate; the orchestrator catches and surfaces it on the SSE stream.

## How to verify

```
.venv/bin/python -m pytest packages/axl_client/tests/ -v
```

Expected: 15 tests pass in roughly 7 seconds (most of the time is in starting and tearing down the threaded HTTP server fixtures).

Sanity check against the upstream binary, no test framework needed:

```
./third_party/axl/node -config third_party/axl/node-config.json &
NODE_PID=$!
.venv/bin/python -c "
from packages.axl_client import AxlClient
c = AxlClient('http://127.0.0.1:9002')
print(c.get_topology().our_public_key[:16], '...')
"
kill $NODE_PID
```

The first 16 hex characters of the local node's public key should print.

## Gensyn surface used

`POST /send`, `GET /recv`, `GET /topology`. Three of the five endpoints registered in `axl/api/handler.go:10-20`. The MCP and A2A endpoints land in later commits.

The request shape is ported from `collaborative-autoresearch-demo/skills/autoresearch-network/research_network.py:71-130` (the `_post` and `_get` helpers).

## Up next

Commit 06 layers `AxlClient.all_peer_ids()` on top of `get_topology()`, deduplicating direct peers and tree entries and removing self, exactly as `research_network.py:214-234` does. Commit 07 boots two real AXL binaries and exchanges one envelope between them, the integration test that proves we can talk to a real mesh.
