# 08. Orchestrator spawner

## What changed

- New module `packages/orchestrator/` with `spawner.py`. Defines `NodeSpec` (the input contract for one role node), `NodeHandle` (the output for a running node), `Spawner` (the lifecycle owner), and `SpawnerError`.
- `Spawner.spawn(spec)` allocates an API port, generates an ed25519 PEM, writes a node config JSON with the loopback bootstrap topology pattern (one node listens, all others dial it), starts the AXL subprocess, and waits for `/topology` to respond.
- Constructor injects `keygen`, `popen`, and `wait_ready` so unit tests can avoid actually spawning anything.
- Context-managed: `with Spawner(...) as s:` stops every spawned node on exit, in reverse order so peers go down before the bootstrap.
- 13 unit tests in `packages/orchestrator/tests/test_spawner.py` cover the spawn lifecycle, the bootstrap-listens-peers-dial topology pattern, single-bootstrap enforcement, key and config emission, explicit port override, port auto-increment, handles immutability, stop_all idempotence, context manager exit, missing binary error, ready-timeout cleanup, and port-in-use skipping.

## Why

The integration test in commit 07 used an ad-hoc `axl_node()` context manager. The orchestrator needs a population of nodes per simulation, indexed by role and role-index, with consistent port allocation and clean shutdown. Generalising the helper into a class lets the rest of the orchestrator (SSE multiplexer in commit 09, FastAPI app in commit 10, choreography in commit 22) treat node spawning as a single primitive.

The dependency injection on `popen`, `keygen`, and `wait_ready` keeps the unit ring fast and binary-free. The integration ring (commit 07 plus future commits) uses the real implementations.

The bootstrap topology pattern matches what the autoresearch demo does for local mode and what we proved works in commit 07. One node sets `Listen=["tls://127.0.0.1:9100"]` (the bootstrap), every other node sets `Peers=["tls://127.0.0.1:9100"]`. Yggdrasil discovers the spanning tree from there. No external network.

## How to verify

```
.venv/bin/python -m pytest packages/orchestrator/tests/test_spawner.py -v
```

Expected: 13 tests pass in under 100ms.

End-to-end smoke against a real binary (manual, not part of the unit ring):

```python
from pathlib import Path
from packages.orchestrator import NodeSpec, Spawner

with Spawner(base_dir=Path("/tmp/spawner_smoke"),
             axl_bin=Path("third_party/axl/node")) as s:
    org = s.spawn(NodeSpec(name="organiser", is_bootstrap=True))
    d0 = s.spawn(NodeSpec(name="designer.0"))
    d1 = s.spawn(NodeSpec(name="designer.1"))
    print([h.api_port for h in s.handles])
```

Boots three real AXL nodes peered through 127.0.0.1:9100. Stops them on exit.

## Gensyn surface used

The same `axl/cmd/node` binary plus the JSON config format from `axl/cmd/node/config.go`. Same loopback-bootstrap pattern as commit 07. No new endpoints exercised here; the spawner is pure process management and config emission.

## Up next

Commit 09 introduces the SSE multiplexer. Each spawned role process emits structured events to the orchestrator over a unix socket; the multiplexer fans them into one Server-Sent Events stream that the web UI subscribes to. Commit 10 layers a FastAPI app on top so the browser can POST `/api/sim` to start a simulation.
