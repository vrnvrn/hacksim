"""HackSim role workers.

Every role node in a simulation pairs an AXL binary with a Python role
worker. The worker reads its identity from environment variables set by
the orchestrator's Spawner, talks to its local AXL node through the
`hacksim-network` skill, and runs a phase-driven event loop that
listens for envelopes and broadcasts its own.

Each role module under this package exports a single `run(ctx)` entrypoint.
The shared CLI in `packages/agents/worker.py` dispatches by the
`HACKSIM_ROLE` env var.

Lite mode (default for the demo) runs the role logic in the worker
process directly using the Anthropic SDK. Claude Code mode (stretch)
uses the same protocol but launches a Claude Code session in the working
directory. Both modes share this package.
"""
