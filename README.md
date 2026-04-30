# HackSim

> Run your own hackathon with agents.

Type one prompt. A swarm of autonomous agents on a peer-to-peer Gensyn AXL mesh designs the bounties, forms teams, writes real code, scores submissions, and crowns the winners. You watch it happen in your browser, then click any winning project and play with what the agents built.

**Built at ETHGlobal Open Agents 2026** for the Gensyn AXL bounty (Best Application of the Agent eXchange Layer). HackSim is the project; Gensyn AXL is the peer-to-peer transport it runs on. We are not affiliated with Gensyn.

Repo: [github.com/vrnvrn/hacksim](https://github.com/vrnvrn/hacksim).

## What HackSim does

You type a prompt like `a research hackathon on protein folding` or `an onchain agents hackathon with five sponsors and a $5k pool`. HackSim spawns a small population of agents that each play one role:

- **Organiser**, one per sim. Reads the prompt, kicks off phases, tallies the leaderboard.
- **Bounty designers**, three by default. Each is a sponsor with a name, a budget, and an opinion about what they want built.
- **Builders**, eight by default. Each has a skill profile. They form teams, write a single-page web project into a real working directory, git-commit the result.
- **Judges**, three by default. Each writes its own rubric, reads the submitted project files, and scores every project against that rubric.

Every agent runs its own AXL node. The orchestrator only spawns processes and serves the UI. Every cross-agent byte goes through the Yggdrasil mesh AXL builds on top of, end to end encrypted, no central message broker.

## What is Gensyn AXL

[AXL](https://docs.gensyn.ai/tech/agent-exchange-layer) is Gensyn's Agent eXchange Layer: a single Go binary that gives any application an encrypted peer-to-peer communication layer with no servers, no cloud, and no accounts. Your code talks to localhost; AXL handles encryption, routing, and peer discovery across the mesh. Anything that can make HTTP requests can use it.

In one paragraph: each AXL node has its own ed25519 identity, joins a peer mesh by dialling a bootstrap, and exposes five HTTP endpoints on `127.0.0.1:9002` (`/topology`, `/send`, `/recv`, `/mcp/{peer}/{service}`, `/a2a/{peer}`). Every byte between nodes is encrypted twice (TLS plus Yggdrasil end-to-end). AXL ships with built-in MCP and A2A integration for typed addressed calls between agents.

HackSim is one possible "Agent Town" answer to the bounty's open prompt. The full AXL source is at [github.com/gensyn-ai/axl](https://github.com/gensyn-ai/axl).

## Quickstart

From a clean clone:

```bash
git submodule update --init --recursive
make build-axl
make hooks-install
make demo
```

`make demo` boots the FastAPI orchestrator and the Next.js dev server together, opens `http://localhost:3000`, and waits for you to type a prompt or click an example.

The default demo population is **1 organiser, 3 bounty designers, 8 builders, 3 judges** (15 AXL nodes peering on loopback). `make smoke` runs a scaled-down headless variant (3 designers, 4 builders, 3 judges) so the harness fits a CI minute; the wire shape is identical.

### Prerequisites

- Go 1.25.5 or newer (for the AXL binary).
- Node 20 or newer with `pnpm` (for the web UI).
- Python 3.10 or newer.
- `openssl` (for ed25519 keys).
- Optional: an `ANTHROPIC_API_KEY` exported in the shell. Without one, every agent falls back to a deterministic stub that still produces real, distinct output. With one, every decision and every project HTML upgrades to a Claude haiku 4.5 call.

## How HackSim uses AXL

Five AXL surfaces exercised by every cross-agent flow:

1. **Discovery** via `GET /topology`. We pull peers from the topology endpoint and union direct peers with the spanning tree, the same algorithm Gensyn's autoresearch demo uses.
2. **Routing** via the Yggdrasil mesh AXL ships with. Every peer id is the public half of an ed25519 keypair; routing is automatic.
3. **End-to-end encryption** via two layers: TLS on the peering link and Yggdrasil end-to-end above it.
4. **Broadcast** via `POST /send`. Bounty announcements, team formations, project submissions, verdict publications. We add a re-broadcast and gossip pattern on top so the mesh propagates reliably on a fresh local network.
5. **Typed addressed calls** via `POST /mcp/{peer}/{service}`. Builders call `judge/score` over JSON-RPC across the mesh; the local Python MCP router dispatches to the right service. This is the layer Gensyn's autoresearch demo does not exercise; HackSim does.

The full mapping from judging criterion to code lives in [docs/process/](docs/process/), where every commit ships a five-section process note explaining what changed, why, how to verify, which AXL surface it exercises, and what comes next.

## For Gensyn judges

We mapped each judging criterion to the code paths and docs that satisfy it.

| Criterion                  | Where to look                                                                          |
|----------------------------|----------------------------------------------------------------------------------------|
| Depth of AXL integration   | `packages/skills/hacksim-network/` (skill mirrors the autoresearch-network shape), `packages/agents/*/role.py` (typed MCP calls and gossip across the mesh) |
| Quality of code            | Conventional Commits, every commit tested, [docs/process/](docs/process/) per commit, writing-rule pre-commit hook |
| Clear documentation        | This README, [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/AGENTS.md](docs/AGENTS.md), the per-commit process notes |
| Working examples           | `make demo` boots a full sim; click any winner card to play the project the agents built |

Qualification gate ("communication across separate AXL nodes, not in-process"): every role runs its own AXL binary with its own ed25519 identity. `tcpdump lo0` during a run shows only HTTP to `127.0.0.1:9002` and the AXL TLS peering port. Every cross-agent message went through Yggdrasil.

## Architecture

Brief diagram. Full version in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

```
       browser UI (Next.js)
              │
       orchestrator (FastAPI)
        │     │      │     │
   ┌────┘     │      │     └────┐
Organiser  Designer  Builder   Judge
  AXL       AXL      AXL       AXL
   └─────── Yggdrasil mesh ─────┘
```

Each role process owns:

1. One AXL node (the Go binary), with its own ed25519 key and ports.
2. One Python role worker (lite mode) or one Claude Code session (stretch mode) running its persona.
3. The `hacksim-network` skill, wrapping the local AXL HTTP API as a small set of helpers.
4. A `CLAUDE.md` persona file holding the role's brief.

Builders also own a working tree where they write project artefacts. Judges read those artefacts directly from the filesystem to score them.

## Status

Built during ETHGlobal Open Agents 2026. The full system runs end to end with `make demo` and produces a real leaderboard of projects you can open in your browser. Track the build chronologically in [docs/process/](docs/process/) (every commit ships a process note).

## License

MIT, see [LICENSE](LICENSE).
