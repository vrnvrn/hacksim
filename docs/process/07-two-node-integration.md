# 07. Two-node integration test

## What changed

- New helper `tests/integration/_axl_node.py`. Generates an ed25519 PEM key with `openssl`, writes a node config JSON, boots an AXL node as a subprocess, polls `/topology` until ready, exposes a `NodeHandle` with `api_url`, `api_port`, `tcp_port`, and a context manager that always tears down.
- New integration test `tests/integration/test_two_node_send.py`. Boots Alice (Listen=`tls://127.0.0.1:9100`) and Bob (Peers=`tls://127.0.0.1:9100`), waits for Bob's `/topology` to show Alice via `AxlClient.all_peer_ids()`, encodes a HackSim Envelope, sends it from Bob to Alice via `POST /send`, drains it on Alice via `GET /recv`, decodes and asserts on every field.
- Test is gated on the AXL binary existing and on `openssl` being on PATH. Skipped cleanly when either is missing so the unit ring stays fast.

## Why

Until this commit the AXL surface was exercised only against `FakeAxl`, a stdlib HTTP fixture. That proves `AxlClient` calls the right URLs with the right headers, but proves nothing about whether the real Go binary, the Yggdrasil mesh, the TCP multiplexer, the `/recv` queue, and our envelope encoding interoperate correctly. This test does.

It also surfaced a real fact about AXL that the documentation does not state explicitly: the `X-From-Peer-Id` header on `/recv` is derived from the routed Yggdrasil IPv6, which encodes only the first 13 bytes of the sender's ed25519 public key (the rest is padded with `f`). See `axl/internal/tcp/listen/listener.go:200` (`peerIDFromAddr`) for the derivation. Authoritative sender identity comes from the envelope's `sender_id` field, set by the sending application. The test asserts prefix equality on `from_peer_id` and full equality on `decoded["sender_id"]`. We document this in the test comment so future contributors do not assume the header is the full peer id.

A second fact: both nodes must use the same `tcp_port` value. AXL's `/send` dials the destination at `<peer_ipv6>:<local_tcp_port>`. The destination port is the LOCAL config's `tcp_port`, used as both listener port and dialler port (see `axl/internal/tcp/dial/dial.go`). So two nodes on one machine can share `tcp_port=7000` because the listener binds to the gVisor netstack on the Yggdrasil-derived IPv6, not on the host loopback. The test sets both Alice and Bob to `tcp_port=7000`. We document this in a comment, since it is the kind of thing that costs an hour the first time you hit it.

## How to verify

```
make build-axl
.venv/bin/python -m pytest tests/integration/test_two_node_send.py -v
```

Expected: 1 test passes in roughly 3 seconds. The harness boots Alice on api port 9202, boots Bob on api port 9212, waits for them to peer, sends one 173-byte envelope, asserts the round-trip, tears both nodes down.

If the AXL binary is not built, the test is skipped with a clear reason. If `openssl` is not on PATH, the test is also skipped. The unit ring (commits 04, 05, 06) does not require either.

## Gensyn surface used

End to end:

- `GET /topology` for peer discovery (`axl/api/topology.go`).
- `POST /send` to dial the destination via Yggdrasil and write a length-prefixed payload (`axl/api/send.go:30-85`).
- The TCP listener accepts the inbound connection, demultiplexes (no MCP/A2A streams registered in this config), and pushes the unclaimed payload to `DefaultRecvQueue` (`axl/internal/tcp/listen/listener.go:213-275`).
- `GET /recv` drains one message with the `X-From-Peer-Id` header set (`axl/api/recv.go`).

This is four of the five HTTP endpoints in `axl/api/handler.go:10-20` exercised by one test. Only `/mcp/` and `/a2a/` are not yet covered; those land in the agent commits.

## Up next

Commit 08 introduces the orchestrator's `Spawner`, which generalises the `axl_node` helper from this commit so the orchestrator can bring up an arbitrary number of nodes with arbitrary names and peer them through a single bootstrap.
