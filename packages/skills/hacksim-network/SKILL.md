---
name: hacksim-network
description: |
  Slash commands for HackSim agents to talk to their local AXL node over the
  Yggdrasil mesh. Mirrors the shape of Gensyn's autoresearch-network skill,
  with HackSim-specific commands for the bounty / build / judge lifecycle.
---

# hacksim-network

In the default `make demo` path, every HackSim role runs as a Python
worker under the orchestrator's Spawner (`packages/agents/<role>/role.py`).
The worker imports `hacksim_network.py` directly; the slash commands
listed below wrap the same module so a Claude Code session can drive the
mesh interactively if you opt into one. The skill exists for both call
paths.

The wire format mirrors Gensyn's `skills/autoresearch-network/` from the
collaborative-autoresearch-demo. The JSON envelope shape, the fan-out
broadcast loop over `/send`, and the recv drain (dedupe by
sender/type/id) are taken from `research_network.py` verbatim.

## Environment

Three variables must be set in the agent's working directory shell:

- `AXL_API_PORT`: the port the local AXL node serves its HTTP bridge on
  (e.g. `9202` for the organiser, `9212` for designer 0, etc.).
- `HACKSIM_ROLE`: the agent's role label (`organiser`, `designer`,
  `builder`, or `judge`).
- `HACKSIM_SIM_ID`: the parent simulation's id, used as the
  `sim_id` field on outgoing envelopes.

The orchestrator's Spawner sets these when it launches the role process.

## Commands

| Slash command       | What it does                                                                    |
|---------------------|---------------------------------------------------------------------------------|
| `/status`           | Print our peer id, IPv6, peer count, and recv queue depth.                      |
| `/recv`             | Drain the local /recv queue, return all pending envelopes as JSON.              |
| `/post-bounty`      | Designer only: broadcast a `bounty.posted` envelope from a JSON arg.            |
| `/submit-project`   | Builder only: broadcast a `project.submitted` envelope with commit hash.        |

Each command exits 0 on success. Output is JSON unless the command says
otherwise. Errors print to stderr and exit non-zero.

Judges read submitted artefacts directly from the filesystem and
broadcast `verdict.published` over `/send`; the organiser tallies
verdicts in-process and broadcasts `hackathon.closed`. Neither path
needs a slash command. If you wire MCP-based judging in a future commit,
add a `/score-project` row here; do not document it ahead of the code.

## Implementation

The Python implementation lives in `hacksim_network.py` next to this
file. The slash commands shell out to `python -m
packages.skills.hacksim_network.hacksim_network <command> [args]`.
