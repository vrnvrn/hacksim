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
2. **Team formation.** Each builder picks the bounty that best fits its skill profile and broadcasts `team.formed` as a solo team (one builder per team). Multi-builder teams are out of scope for this submission; the protocol carries one envelope type for this phase (`team.formed`), and any multi-builder iteration would add new types rather than reuse existing ones.
3. **Build.** Each builder writes `index.html`, `style.css`, and `app.js` into its working directory, runs `git init && git add && git commit`, and broadcasts `project.submitted` with the commit hash and entry path. The builder also `POST`s artefact metadata to the orchestrator over a separate HTTP channel; the orchestrator runs `git archive` on the working tree and serves the result under a strict CSP.
4. **Judging.** Each `Judge` worker reads project files directly from the filesystem (artefacts already registered with the orchestrator), composes a five-criterion rubric weighted by its archetype, and broadcasts `rubric.published` and one `verdict.published` per project.
5. **Showcase.** The organiser tallies verdicts, broadcasts `hackathon.closed` with the leaderboard, and the snapshot accumulator on the orchestrator side drives the live page transition to phase 4. Each winner card opens a three-tab modal (Demo, Code, Verdict) over the artefacts the orchestrator served in step 3.

The detailed envelope shape and dedupe rules live in `packages/protocol/envelopes.py` and `packages/agents/_runtime.py`.

## AXL surfaces in use

<a id="surfaces"></a>
Four of AXL's HTTP surfaces carry every cross-agent message:

- `GET /topology`: peer enumeration. The algorithm unions direct peers with the spanning tree and drops the local public key. Ported verbatim from Gensyn's `research_network.py`.
- `POST /send`: unicast fan-out. The runtime broadcasts by iterating peers and POSTing once per destination. `WorkerState.fanout` schedules timed re-broadcasts and `WorkerState.broadcast_now` is the per-tick fan-out, with gossip-style reforward after dedupe so freshly joined peers also see the envelope.
- `GET /recv`: per-node inbox drain. Workers dedupe on `(sender_id, type, payload_id)` before dispatching to a per-envelope handler.
- `POST /mcp/{peer}/{service}`: typed JSON-RPC. Used by the organiser during the JUDGING phase to confirm each judge's verdict against a project. The judge node runs an aiohttp side-car (`packages/agents/judge/mcp_service.py`) on a spawner-allocated port; the AXL Go binary is configured with `router_addr` plus `router_port` so inbound MCP traffic gets forwarded to the side-car. See [#mcp](#mcp) below for the full call shape.

AXL also ships `/a2a/{peer}` for streaming. HackSim does not exercise that surface in this submission.

## MCP round trip

<a id="mcp"></a>
The MCP surface is supplemental: every verdict still rides the envelope path (`verdict.published`). The MCP call confirms the same verdict over a typed transport so the SSE stream shows the JSON-RPC round trip happening live.

Wire shape:

1. The organiser POSTs to `http://<local_axl>/mcp/<judge_peer>/judge` with a JSON-RPC `tools/call` for `score_project`.
2. AXL wraps the body as an `MCPMessage{service, request, from_peer_id}` envelope and tunnels it through Yggdrasil to the destination peer's TCP listener.
3. The destination AXL POSTs `{service, request, from_peer_id}` to the configured router URL (`http://127.0.0.1:<router_port>/route`).
4. The judge's aiohttp side-car runs `decisions.score_project` and returns the verdict in `content[*].text` (MCP convention) plus `structuredContent` (the same dict, parsed).
5. The reply unwinds back to the caller as a JSON-RPC response.

Code paths:

| Concern | File |
|---|---|
| Caller helper | [packages/axl_client/client.py](../packages/axl_client/client.py) `mcp_call` |
| Service definition | [packages/agents/judge/mcp_service.py](../packages/agents/judge/mcp_service.py) |
| Side-car lifecycle inside the judge worker | [packages/agents/judge/role.py](../packages/agents/judge/role.py) |
| Router config plumbing | [packages/orchestrator/spawner.py](../packages/orchestrator/spawner.py) `mcp_router_port`, `with_mcp_router` |
| Driver loop | [packages/agents/organiser/role.py](../packages/agents/organiser/role.py) `_confirm_via_mcp` |
| End-to-end test | [tests/integration/test_mcp_round_trip.py](../tests/integration/test_mcp_round_trip.py) |

## Replay

<a id="replay"></a>
Every running sim is mirrored to disk by `packages/orchestrator/recorder.py`. The recorder subscribes to the SSE hub via `add_publish_listener` and appends every event as one JSON line to `sim-runs/<sim_id>/events.jsonl`. The first line is a meta record (sim id, prompt, started-at, config); each subsequent line is `{"t": <seconds>, "type": <event-type>, "data": <payload>}`.

Three endpoints expose recordings:

- `GET /api/replay` lists every recording on disk with prompt, duration, and event count.
- `GET /api/replay/{run_id}/snapshot` returns the final accumulated snapshot, mirroring `/api/sim/{id}/snapshot`.
- `GET /api/replay/{run_id}/stream` streams the events as SSE with an optional `speed` query param (1 = original cadence; default 4 = four times faster). Inter-event sleeps are clamped to 5 seconds so a quiet phase never stalls the viewer; `replay.started` and `replay.finished` bracket the stream.

The frontend's `/replay/[runId]` route reuses the live page's components against the replay endpoints. A judge clicking the hosted preview can watch a real recorded run end to end without a local install.

## What changed from autoresearch

Gensyn ships a reference application for AXL, the [collaborative-autoresearch-demo](https://github.com/gensyn-ai/collaborative-autoresearch-demo). HackSim treats `research_network.py` as a sibling and ports the transport patterns verbatim. A maintainer auditing depth of integration can read the deltas line by line:

| Pattern | Autoresearch | HackSim | Where in HackSim |
|---|---|---|---|
| `_post` and `_get` over urllib | `research_network.py` urllib helpers | identical shape | [packages/axl_client/client.py:35-100](../packages/axl_client/client.py#L35) |
| Peer enumeration unions `peers` and `tree` | `research_network.py:214-234` | identical algorithm, different field names | [packages/axl_client/client.py:182-210](../packages/axl_client/client.py#L182) |
| Fan-out broadcast loop | `research_network.py:285-298` | same shape; we wrap the loop in `WorkerState.broadcast_now` | [packages/agents/_runtime.py:87-122](../packages/agents/_runtime.py#L87) |
| Drain loop | `research_network.py:320-374` | one delta: dedupe key is `(sender_id, type, payload_id)` instead of `(sender_id, round_num)` to handle seven envelope types in a phased lifecycle instead of one in a flat topology | [packages/agents/_runtime.py:141-215](../packages/agents/_runtime.py#L141) |
| Skill manifest as the integration primitive | `skills/autoresearch-network/` exposes `/status`, `/recv`, `/broadcast` (three commands) | `packages/skills/hacksim-network/` exposes `/status`, `/recv`, `/post-bounty`, `/submit-project` (four commands, mapped to role responsibilities) | [packages/skills/hacksim-network/](../packages/skills/hacksim-network/) |
| Number of envelope types | one (`research.contribution`) | seven (`bounty.posted`, `team.formed`, `project.submitted`, `rubric.published`, `verdict.published`, `phase.tick`, `hackathon.closed`) | [packages/protocol/envelopes.py](../packages/protocol/envelopes.py) |
| Topology shape | flat (every peer equal) | typed roles in a phased lifecycle (organiser, bounty designer, builder, judge) | [packages/agents/](../packages/agents/) |
| Gossip / re-broadcast | autoresearch re-shares each finding once per cycle | HackSim schedules two delayed re-broadcasts via `WorkerState.fanout` plus gossip-on-receive after dedupe | [packages/agents/_runtime.py:124-146](../packages/agents/_runtime.py#L124) |

The transport is unchanged; the application shape, the lifecycle, and the artefact pipeline are HackSim's contribution.

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
