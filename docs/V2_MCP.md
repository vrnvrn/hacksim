# V2: wiring an MCP-based judge round trip (shipped)

This file was originally a forward design sketch for a feature HackSim chose not to ship in v1. The feature shipped: see [docs/ARCHITECTURE.md#mcp](ARCHITECTURE.md#mcp) for the live shape and the integration test at [tests/integration/test_mcp_round_trip.py](../tests/integration/test_mcp_round_trip.py).

## Why we did ship it

The bounty rubric leads with depth of AXL integration. The unicast envelope path on `/topology`, `/send`, and `/recv` qualifies us, but the typed `/mcp/{peer}/{service}` surface is the one Gensyn highlights on the AXL landing page. Adding the round trip exercises four of the five HTTP surfaces and proves the typed JSON-RPC flow works on real binaries, not just on a sketch.

## What landed

The original four-step plan (per-node router config, per-judge aiohttp side-car, `AxlClient.mcp_call`, organiser driver) plus the integration test landed in commit `6caae9f feat(agents+axl): MCP round trip wired end to end`. The driver runs as a confirmation pass: envelopes remain the source of truth, so every existing unit test continues to pass and the snapshot accumulator is unchanged. The organiser broadcasts `mcp.score_requested` and `mcp.score_received` per call so the SSE stream surfaces the typed surface firing live.

## What we deliberately scoped out

A2A streaming. AXL also ships `/a2a/{peer}` for typed streaming RPC. HackSim does not exercise it; the lifecycle is request/reply, not stream-shaped, and adding A2A would have been depth-of-integration cosmetic, not functional. Future work for forks that want a five-of-five surface count.
