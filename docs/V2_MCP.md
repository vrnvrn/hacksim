# V2: wiring an MCP-based judge round trip

This file is a forward design sketch, not a shipped path. HackSim's current submission exercises three AXL HTTP surfaces (`/topology`, `/send`, `/recv`). AXL also ships `/mcp/{peer}/{service}` for typed JSON-RPC across the mesh, and the architecture supports wiring one MCP-based call without changing the rest of the stack. This document describes the four-step shape so a fork can pick it up.

## Why we did not ship it for v1

Ship cost is roughly four hours of new code plus two integration tests, with the long pole being the per-judge aiohttp side car and the AXL-side router config plumbing. The v1 submission shape (recorded video plus repo plus `make demo`) does not need MCP to satisfy the qualification gate or the judging rubric. The rubric rewards depth of AXL integration, code quality, clear documentation, and working examples; the unicast envelope path plus `tests/integration/test_two_node_send.py` carries depth, and adding an MCP path now would risk introducing a flaky surface for marginal credit.

## What AXL exposes on the destination side

The destination AXL node listens on its bridge port for `POST /mcp/{peer}/{service}`. When a request lands, AXL wraps the inner JSON-RPC body as an `MCPMessage{service, request, from_peer_id}` envelope, dials the destination peer over the Yggdrasil-routed TCP listener, and forwards length-prefixed bytes (`third_party/axl/api/mcp.go`). On the destination, `MCPStream.Forward` (`third_party/axl/internal/mcp/mcp_stream.go`) unwraps the envelope and POSTs `{service, request, from_peer_id}` to the local "router URL" configured at startup time (`third_party/axl/cmd/node/main.go:98-102`). The router URL format is `http://<router_addr>:<router_port>/route`. The router responds with `{response, error}`, AXL re-wraps it as an `MCPResponse`, and ships it back to the origin AXL node which un-wraps and returns it to the original HTTP caller as the JSON-RPC reply.

## Four steps to wire one path

### Step 1: per-node router config in the spawner

`packages/orchestrator/spawner.py` writes a per-node config JSON. Add `router_addr` and `router_port` fields to that dict for judge nodes. The Spawner allocates a fresh port per judge router (alongside the existing `api_port` allocation) and sets `router_addr=http://127.0.0.1` and `router_port=<allocated>`. Builder, designer, and organiser nodes do not get router config (they are MCP origins, not destinations).

### Step 2: per-judge aiohttp router side car

Each judge process spawns one aiohttp server bound to `127.0.0.1:<router_port>` exposing `POST /route`. The handler receives `{service, request, from_peer_id}`, dispatches by service name (currently just `"judge"`), parses the inner JSON-RPC, calls `score_project` from `packages/agents/judge/decisions.py`, and returns the verdict in the response shape AXL expects (`{response: <jsonrpc-response>, error: ""}`). Lifecycle: start the aiohttp server before the role's run loop, stop it on `SIGTERM`. About 80 lines.

### Step 3: AxlClient.mcp_call

Add a method to `packages/axl_client/client.py` that POSTs a JSON-RPC request to `http://<api_url>/mcp/<peer_id>/<service>`. About 30 lines including the response unwrap.

### Step 4: organiser drives phase-3 verdicts via mcp_call

`packages/agents/organiser/role.py` learns the judge peer ids from snapshot updates. On `phase.tick JUDGING` the organiser calls `axl_client.mcp_call(judge_peer, "judge", {"method": "tools/call", "params": {"name": "score", "arguments": {"project_id": "..."}}})` for each (judge, project) pair, receives the verdict, and broadcasts `verdict.published` as today (so the snapshot accumulator and the live page see no shape change). About 40 lines plus a refactor to extract the existing organiser "wait for verdicts" loop.

### Step 5: integration test

`tests/integration/test_mcp_round_trip.py` boots two AXL binaries with router config, runs the aiohttp side car on one, and asserts a JSON-RPC round trip end to end. About 100 lines, mirrors the shape of `test_two_node_send.py`.

## What to update once it ships

- `apps/web/components/Faq.tsx`: surface count goes from three back to four; the "MCP-based judging is on the v2 list" line is removed.
- `apps/web/components/HeroExamplesAside.tsx`: no change.
- `README.md`: surface paragraph names four exercised endpoints.
- `packages/skills/hacksim-network/SKILL.md`: command table gains a `/score-project` row.
- `tests/integration/test_mcp_round_trip.py`: new.
- This file: archive.

## Why this design preserves the rest of the stack

The verdict envelope shape and the snapshot accumulator do not change. The live page and the showcase modal continue to read verdicts off the snapshot. The qualification gate is already satisfied by the unicast path; MCP adds depth, not new gate satisfaction.
