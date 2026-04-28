---
name: hacksim-network
description: |
  Slash commands for HackSim agents to talk to their local AXL node over the
  Yggdrasil mesh. Mirrors the shape of Gensyn's autoresearch-network skill,
  with HackSim-specific commands for the bounty / build / judge lifecycle.
---

# hacksim-network

Each role in a HackSim simulation runs a Claude Code session with this
skill installed. The slash commands wrap the local AXL HTTP API at
`127.0.0.1:$AXL_API_PORT` so the agent never has to write urllib code by
hand.

This skill mirrors `skills/autoresearch-network/` from Gensyn's
collaborative-autoresearch-demo. The wire format is the same JSON
envelope shape, the broadcast loop is the same fan-out over `/send`, the
recv drain is the same dedupe-by-(sender, type, id).

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
| `/score-project`    | Judge only: call `/mcp/{builder_peer}/judge tools/call score` over the mesh.    |
| `/demo-project`     | Judge only: render a project artefact in headless Playwright, return summary.   |
| `/leaderboard`      | Organiser only: tally verdicts, return ranked list.                             |

Each command exits 0 on success. Output is JSON unless the command says
otherwise. Errors print to stderr and exit non-zero.

## Implementation

The Python implementation lives in `hacksim_network.py` next to this
file. The slash commands shell out to `python -m
packages.skills.hacksim_network.hacksim_network <command> [args]`.
