"""HackSim role workers.

Every role node in a simulation pairs an AXL binary with a Python role
worker. The worker reads its identity from environment variables set by
the orchestrator's Spawner, talks to its local AXL node through the
`hacksim-network` skill, and runs a phase-driven event loop that
listens for envelopes and broadcasts its own.

Each role module under this package exports a single `run(ctx)` entrypoint.
The shared CLI in `packages/agents/worker.py` dispatches by the
`HACKSIM_ROLE` env var.

Each role has two decision paths that emit the same envelope shape:

- A deterministic stub keyed off the worker's peer id and the prompt.
  Default. Runs without `ANTHROPIC_API_KEY` set, useful for CI and for
  first-time reviewers who have not set up a key.
- A Claude-driven path that calls the Anthropic SDK against the role's
  CLAUDE.md persona prompt. Activated when `ANTHROPIC_API_KEY` is set
  on the worker process.

Both paths produce real, on-theme output. The stub is not a placeholder.
"""
