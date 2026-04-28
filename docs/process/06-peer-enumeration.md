# 06. Peer enumeration on AxlClient

## What changed

- Added `AxlClient.all_peer_ids()` to `packages/axl_client/client.py`. It calls `get_topology()` and returns the deduplicated list of all peer ids reachable on the mesh, with self removed.
- Algorithm: take every direct peer that is `up`, union with every entry in the tree, discard our own public key, return the unsorted list.
- 10 new tests in `packages/axl_client/tests/test_peer_enumeration.py` cover empty mesh, direct-only, tree-only, unioned dedup, down-peer skipping, down-peer recovery via tree, self-discard, return type guarantee, missing optional fields, and a realistic mesh shape.

## Why

This is the second-most-load-bearing function in the autoresearch demo, after `_post`. Every fan-out broadcast in HackSim (bounty announcements, project submissions, verdict publications) iterates over the result of this call. The orchestrator's choreography also uses it to know how many agents are actually connected.

The algorithm is ported verbatim from `research_network.py:214-234`. The reason for the union is that direct peers are nodes we have a TCP session with right now, while the tree includes every node Yggdrasil knows how to route to. A peer can be in the tree without being in the direct list (multi-hop) and a peer can drop out of the direct list while remaining in the tree. Iterating over both gives us the largest reachable set without double-sending.

We discard `up=False` direct peers because sending to them would dial-fail at the AXL layer (axl/api/send.go raises a dial error for offline peers). Tree entries do not carry an `up` field; if Yggdrasil knows about a node in the tree, the optimistic assumption is that it can be reached.

## How to verify

```
.venv/bin/python -m pytest packages/axl_client/tests/test_peer_enumeration.py -v
```

Expected: 10 tests pass in roughly 5 seconds.

Sanity check against the upstream binary:

```
./third_party/axl/node -config third_party/axl/node-config.json &
NODE_PID=$!
.venv/bin/python -c "
from packages.axl_client import AxlClient
c = AxlClient('http://127.0.0.1:9002')
peers = c.all_peer_ids()
print(f'discovered {len(peers)} peers via Gensyn bootstrap')
for p in peers[:5]: print(' ', p[:16], '...')
"
kill $NODE_PID
```

When the local node has connected to the Gensyn public bootstrap peers, this prints however many other nodes currently exist on the public mesh.

## Gensyn surface used

`GET /topology` plus the dedup logic from `collaborative-autoresearch-demo/skills/autoresearch-network/research_network.py:214-234`. No new endpoints. This commit is the algorithmic side of `get_topology()`, exactly as the autoresearch demo separates them.

## Up next

Commit 07 boots two real AXL binaries, points them at a shared loopback bootstrap, and exchanges one envelope between them. That is the first commit where HackSim talks to a real mesh and the integration test ring lights up.
