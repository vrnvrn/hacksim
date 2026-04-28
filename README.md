# HackSim

> Run your own hackathon with agents.

Type one prompt. Autonomous agents on a Gensyn AXL mesh design the bounties, form teams, write real code, score submissions, and crown the winners. You watch it happen in your browser, then click any winning project and play with what the agents built.

A submission for the Gensyn AXL hackathon. Built on [AXL](https://github.com/gensyn-ai/axl), the Agent eXchange Layer. Inspired by Gensyn's [collaborative-autoresearch-demo](https://github.com/gensyn-ai/collaborative-autoresearch-demo).

## What is HackSim

HackSim is an Agent Town. Every role in the hackathon is an autonomous agent running its own AXL node, peering with the others through the Yggdrasil mesh, talking peer to peer. There is no central coordinator. The orchestrator only spawns processes and serves the UI; every cross-agent byte traverses a real AXL mesh.

- **Organiser**, one per sim. Reads the human prompt, kicks off phases, tallies the leaderboard.
- **Bounty Designers**, three by default. Each is a "sponsor" with a name, a budget, and an opinion about what they want built.
- **Builders**, eight by default. Each has a skill profile. They form teams, write a single-page web project into a real working directory, commit the result.
- **Judges**, three by default. Each writes their own rubric, opens every submission in a sandboxed Playwright browser, scores based on real interactions.

Every agent is a Claude Code session pointed at its own working directory, with a local AXL node and the `hacksim-network` skill that wraps the mesh as slash commands.

## Quickstart

Mirror of AXL's quickstart. From a clean clone:

```bash
git submodule update --init --recursive
make build-axl
make hooks-install
make demo
```

`make demo` boots one organiser, three bounty designers, eight builders, and three judges, opens `http://localhost:3000`, and waits for you to type a prompt.

### Prerequisites

- Go 1.25.5 or newer (for the AXL binary).
- Node 20 or newer with `pnpm` (for the web UI).
- Python 3.10 or newer.
- [Claude Code](https://docs.anthropic.com/claude/docs/claude-code) installed and authenticated.
- `openssl` (for ed25519 keys).

The Anthropic API key needs to be set in `~/.config/claude-code/credentials.json`, the standard Claude Code location.

## How HackSim uses AXL

Five layers of AXL exercised by every cross-agent call:

1. **Discovery** via `GET /topology`. We pull peers from the topology endpoint, exactly as `research_network.py:214-234` does, unioning direct peers with the spanning tree.
2. **Routing** via the Yggdrasil mesh. Every peer id is the public half of an ed25519 keypair; routing is automatic.
3. **End to end encryption** via two layers, TLS on the peering link and Yggdrasil end to end above it.
4. **Broadcast** via `POST /send`. Bounty announcements, project submissions, verdict publications. Fan-out loop adapted from `research_network.py:285-298`.
5. **Typed addressed calls** via `POST /mcp/{peer}/{service}`. Builders call `judge/score` over JSON-RPC. Judges call `registry/submit_project`. The Gensyn autoresearch demo does not exercise this surface; HackSim does.

The full mapping from judging criterion to code lives in [docs/process/](docs/process/), where every commit ships a five-section process note explaining what changed, why, how to verify, which Gensyn surface it exercises, and what comes next.

## For builders

Want to extend HackSim? Replace a role, add a new role, or wire HackSim to your own AXL bootstrap?

- **Replace a role.** Each persona lives at `packages/agents/<role>/CLAUDE.md`. Edit the file, restart the sim, the agent inherits the new brief.
- **Add a role.** Copy an existing role directory, write a new `CLAUDE.md`, add an MCP service if the role needs typed tools, register it with the orchestrator's role table.
- **Point at a public AXL bootstrap.** Edit `scripts/run_sim.sh` and replace the loopback bootstrap with a public peer URI (Gensyn ships `tls://34.46.48.224:9001` and `tls://136.111.135.206:9001`).

See [docs/AGENTS.md](docs/AGENTS.md) for the full role catalogue with persona files verbatim.

## For Gensyn

Mapping the judging criteria to the code that satisfies them.

| Criterion                  | Where to look                                                                          |
|----------------------------|----------------------------------------------------------------------------------------|
| Depth of AXL integration   | `packages/skills/hacksim-network/` (skill mirrors `autoresearch-network`), `packages/agents/*/mcp_*.py` (typed MCP services across the mesh) |
| Quality of code            | Conventional Commits, every commit tested, [docs/process/](docs/process/) per commit   |
| Clear documentation        | This README, [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/AGENTS.md](docs/AGENTS.md), [docs/process/](docs/process/) chronological |
| Working examples           | `make demo` boots a full sim; click any winner card to play the project the agents built |

Qualification gate ("communication across separate AXL nodes, not in-process"): every role runs its own AXL binary with its own ed25519 identity. `tcpdump lo0` during a run shows only HTTP to `127.0.0.1:9002`. Every cross-agent message went through Yggdrasil.

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
2. One Claude Code session, in its own working directory.
3. The `hacksim-network` skill, wrapping the local AXL HTTP API.
4. A `CLAUDE.md` persona file holding the role's brief.

Builders also own a working tree where they write project artefacts. Judges also own a Playwright sandbox for hands-on evaluation.

## Status

This README ships in commit 02. Real Gensyn integration arrives in commit 03 (AXL submodule). Full quickstart works after commit 32 (`make demo`). Track progress in [refs/COMMIT_LOG.md](refs/COMMIT_LOG.md) (local only) and the corresponding [docs/process/](docs/process/) entries (public).

## License

MIT, see [LICENSE](LICENSE).
