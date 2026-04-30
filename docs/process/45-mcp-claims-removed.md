# 45. Drop MCP claims, align surface counts, separate worker from Claude Code

## What changed

The judge review caught three load-bearing user-facing claims that the
worker stack did not back up:

1. README and `Faq.tsx` both claimed HackSim exercises four AXL HTTP
   surfaces, including `/mcp/{peer}/{service}` for typed JSON-RPC
   ("builders call judge.score over Yggdrasil"). `AxlClient` ends at
   `recv`. No HackSim Python file POSTs to `/mcp/` or `/a2a/`.
   Judges score locally in
   `packages/agents/judge/decisions.py`.
2. `SKILL.md` opened with "Each role in a HackSim simulation runs a
   Claude Code session with this skill installed." The default demo
   path runs Python role workers under the orchestrator's `Spawner`.
   Claude Code is not invoked. The FAQ already said so.
3. `SKILL.md` listed `/score-project`, `/demo-project`, and
   `/leaderboard` slash commands. Only four commands actually ship in
   `hacksim_network.py`: `/status`, `/recv`, `/post-bounty`,
   `/submit-project`. The other three rows had no implementation.

Files changed:

- `README.md`: "How HackSim uses AXL" goes from five surfaces to
  three (`/topology`, `/send`, `/recv`). Adds explicit "MCP and A2A
  are upstream and on the v2 list" language so the AXL feature set is
  acknowledged without being claimed. Adds the AXL/HTTP split
  paragraph so "every cross-agent byte" cannot be misread against
  builder artefact POSTs to the orchestrator. Drops the
  "Python role worker (lite mode) or Claude Code session (stretch
  mode)" framing; the default demo path is the Python worker, with
  Claude Code as an opt-in. The criterion table for "depth of AXL
  integration" now points at `_runtime.py` and the integration test
  rather than at MCP claims.
- `apps/web/components/Faq.tsx`: surface count goes from four to
  three. Removes the `/mcp builders call judge.score` bullet. Adds
  the AXL/HTTP split paragraph and an explicit "MCP-based judging is
  on the v2 list" line. The autoresearch comparison loses the
  "we exercise /mcp, autoresearch does not" sentence.
- `packages/skills/hacksim-network/SKILL.md`: preface rewritten to
  describe the Python worker as the default host with Claude Code as
  an opt-in. The command table drops the three rows that never
  landed. A trailing note explains that judges read artefacts from
  the filesystem and verdicts ride `/send`; if MCP-based judging
  ships in a future commit it adds a row, not the other way around.

## Why

The plan's first remediation in §19c was the choice "implement one
MCP path or remove the claim everywhere." Implementing one MCP path
needs four hours of new code: per-node `router_addr`/`router_port` in
the spawner config, a per-judge aiohttp router that demuxes by service
name, an `AxlClient.mcp_call` helper, an organiser change to drive
phase-3 verdicts via that call, and a two-node integration test that
boots both AXL binaries plus the Python router. That is a v2 task,
recorded as such in the plan. For this submission the docs say what
runs.

A README that overstates surfaces invites a panel to grep for the
absent code; a README that underclaims survives the same audit. The
mesh demo plus `tests/integration/test_two_node_send.py` carry the
qualification gate without needing the MCP claim.

## How to verify

```
rg -P 'five surfaces|five HTTP|four AXL HTTP surfaces|judges Playwright' README.md apps/web docs/
```

No matches. The only remaining MCP mentions in `README.md`,
`apps/web/components/Faq.tsx`, and `SKILL.md` are framed as
"AXL ships X; HackSim does not exercise X in this submission" or
"v2 roadmap."

```
rg 'score-project|demo-project|leaderboard' packages/skills
```

The SKILL.md table has no row for any of these. The trailing note
explains why.

```
.venv/bin/pytest packages/ -q
cd apps/web && pnpm exec tsc --noEmit
```

Tests pass; type check clean.

## Gensyn surface used

`POST /send`, `GET /recv`, `GET /topology`. The same three surfaces
the runtime has used since commit 12; the change is documentation
honesty about which surfaces the workers actually exercise.

## Up next

Author `docs/ARCHITECTURE.md` and `docs/AGENTS.md` so the README
links resolve.
