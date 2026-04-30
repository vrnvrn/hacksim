# Architecture

HackSim is an Agent Town built on Gensyn AXL. One prompt creates one simulation. Each role in that simulation runs in its own OS process with its own AXL Go binary; envelopes flow over the AXL mesh. The orchestrator and the Next.js UI sit alongside the mesh, never on the agent control plane.

## High-level diagram

```
                   browser UI (Next.js, Tailwind)
                              |
                              | /api/sim/* (REST + SSE)
                              v
                  orchestrator (FastAPI, Python)
                  spawns AXL nodes, spawns role workers,
                  multiplexes worker stdout into SSE,
                  serves project artefacts as static files
                  |        |          |          |
                  v        v          v          v
            Organiser  Bounty Designer  Builder    Judge
            worker     worker (xK)      worker (xN) worker (xM)
            + AXL      + AXL            + AXL       + AXL
            + key 0    + key i          + key i     + key i
                  |        |          |          |
                  +--------+----------+----------+
                                |
                       Yggdrasil mesh on loopback
                       (TLS bootstrap on 127.0.0.1:9100)
```

Default population: 1 organiser, 3 bounty designers, 8 builders, 3 judges. Fifteen AXL Go processes peering through one TLS bootstrap, each with its own ed25519 keypair and its own HTTP API port.

## What lives where

| Concern | Code |
|---|---|
| AXL HTTP wrapper (POST /send, GET /recv, GET /topology) | `packages/axl_client/client.py` |
| Envelope shape and round-trip helpers | `packages/protocol/envelopes.py` |
| Worker runtime (drain loop, dedupe, fanout, gossip) | `packages/agents/_runtime.py` |
| Role workers (one per role) | `packages/agents/{organiser,bounty_designer,builder,judge}/role.py` |
| Persona files reviewers read | `packages/agents/<role>/CLAUDE.md` |
| Skill that wraps the local AXL HTTP API for both Python workers and an opt-in Claude Code session | `packages/skills/hacksim-network/` |
| AXL node lifecycle (one Go subprocess per role, per-node config files, port allocation) | `packages/orchestrator/spawner.py` |
| Sim controller (composes Spawner, log tailer, snapshot accumulator) | `packages/orchestrator/controller.py` |
| FastAPI app (`POST /api/sim`, `GET /api/sim/{id}/snapshot`, SSE stream, artefact serving) | `packages/orchestrator/api.py`, `packages/orchestrator/artefacts.py` |
| Browser UI | `apps/web/` |

## Message flow, one phase at a time

1. **Bounty design.** Each `BountyDesigner` worker reads the prompt, picks a sponsor archetype keyed off its peer id, composes a bounty, and broadcasts `bounty.posted` over `POST /send` to every peer in `/topology`. `Builder` workers drain `/recv`, dispatch the bounty into a per-builder inbox, and stash it.
2. **Team formation.** Each builder picks the bounty that best fits its skill profile and broadcasts `team.formed`. The current submission ships solo teams (one builder per team); team invites are wired in the wire protocol but not exercised yet.
3. **Build.** Each builder writes `index.html`, `style.css`, and `app.js` into its working directory, runs `git init && git add && git commit`, and broadcasts `project.submitted` with the commit hash and entry path. The builder also `POST`s artefact metadata to the orchestrator over a separate HTTP channel; the orchestrator runs `git archive` on the working tree and serves the result under a strict CSP.
4. **Judging.** Each `Judge` worker reads project files directly from the filesystem (artefacts already registered with the orchestrator), composes a five-criterion rubric weighted by its archetype, and broadcasts `rubric.published` and one `verdict.published` per project.
5. **Showcase.** The organiser tallies verdicts, broadcasts `hackathon.closed` with the leaderboard, and the snapshot accumulator on the orchestrator side drives the live page transition to phase 4. Each winner card opens a three-tab modal (Demo, Code, Verdict) over the artefacts the orchestrator served in step 3.

The detailed envelope shape and dedupe rules live in `packages/protocol/envelopes.py` and `packages/agents/_runtime.py`.

## AXL surfaces in use

Three of AXL's HTTP surfaces carry every cross-agent message:

- `GET /topology`: peer enumeration. The algorithm unions direct peers with the spanning tree and drops the local public key. Ported verbatim from Gensyn's `research_network.py`.
- `POST /send`: unicast fan-out. The runtime broadcasts by iterating peers and POSTing once per destination. `WorkerState.fanout` schedules timed re-broadcasts and `WorkerState.broadcast_now` is the per-tick fan-out, with gossip-style reforward after dedupe so freshly joined peers also see the envelope.
- `GET /recv`: per-node inbox drain. Workers dedupe on `(sender_id, type, payload_id)` before dispatching to a per-envelope handler.

AXL also ships `POST /mcp/{peer}/{service}` for typed JSON-RPC and `/a2a/{peer}` for streaming. HackSim does not exercise either in this submission. Wiring an MCP-based judge round trip is captured in `refs/PLAN.md` section 19c as a v2 task with a complete design (per-node router config in the spawner, per-judge aiohttp router, `AxlClient.mcp_call`, organiser changes, two-node integration test).

## Two channels, one trust boundary

There are two HTTP channels in HackSim:

1. **Agent control plane.** Phase ticks, bounty announcements, team formations, project submissions, rubrics, verdicts, hackathon close. All ride AXL envelopes over `POST /send` and drain via `GET /recv`. Every byte between agents is encrypted twice (TLS plus Yggdrasil end-to-end).
2. **Orchestrator administrative plane.** The browser talks to the orchestrator over `/api/sim/*`. Builders also `POST` artefact metadata to the orchestrator after `git commit` so the showcase iframe can serve the resulting tree under a strict CSP. This channel is filesystem registration, not agent control.

Removing the orchestrator silences the UI and the artefact pipeline; the agents keep talking. Removing AXL silences the simulation.

## Verifying it lives across separate AXL nodes

`tests/integration/test_two_node_send.py` boots two real AXL Go binaries with distinct ports and ed25519 keys, peers them on a loopback bootstrap, has the first POST one envelope to the second, and asserts the receiver drained the same bytes. The orchestrator is not in the loop; the test proves AXL is the wire.

While a sim is running:

```bash
ps aux | grep third_party/axl/node | grep -v grep
lsof -i -P -n | grep -E "node.*LISTEN" | sort
# macOS uses lo0; Linux uses lo.
sudo tcpdump -i lo0 -n 'tcp port 9100 or tcp port 7000' | head -20
```

Stopping every node interrupts the simulation immediately. The AXL Go processes are the system's nervous system; the orchestrator is just the host.
