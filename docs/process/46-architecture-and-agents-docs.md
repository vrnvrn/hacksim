# 46. Author docs/ARCHITECTURE.md and docs/AGENTS.md

## What changed

The README "How HackSim uses AXL" criterion table and the
architecture section both linked to `docs/ARCHITECTURE.md` and
`docs/AGENTS.md`. Neither file existed; only `docs/process/` shipped.
A panel clicking either link saw a 404 on the GitHub mirror.

Files added:

- `docs/ARCHITECTURE.md`: the diagram, the per-process model
  (one AXL Go binary plus one Python role worker per role), the
  message flow phase by phase, the three AXL surfaces in use
  (topology, send, recv) with explicit notes that MCP and A2A are
  upstream and roadmap, the separation between the agent control
  plane on AXL and the orchestrator administrative plane on FastAPI,
  and the verification block (`tcpdump` + `lsof` + `ps`).
- `docs/AGENTS.md`: one section per role (organiser, bounty designer,
  builder, judge), each with the persona excerpt, the code path, the
  inbound and outbound envelopes, and the deterministic-versus-Claude
  decision module split. The judge section explicitly states judges
  read project files from the filesystem and there is no Playwright
  sandbox in this submission, matching the README rewrite from
  commit 45.

No code changes.

## Why

The README link was a broken promise. ARCHITECTURE and AGENTS are
both natural reading material for a judge: the first answers
"how does this fit together" with one diagram and a verification
block; the second answers "what does each role actually do" with the
real envelope set and the real decision-module split. The persona
files under `packages/agents/<role>/CLAUDE.md` already exist; AGENTS
is the index that makes them discoverable.

## How to verify

```
ls docs/ARCHITECTURE.md docs/AGENTS.md
rg 'docs/ARCHITECTURE.md|docs/AGENTS.md' README.md
```

Both files exist; both README links resolve.

The contents are anchored to real code. Spot-check a few names:

```
rg 'all_peer_ids|broadcast_now|fanout' packages/axl_client packages/agents/_runtime.py
ls packages/agents/*/CLAUDE.md
ls tests/integration/test_two_node_send.py
```

Each path called out in the docs exists.

## Gensyn surface used

None directly; ARCHITECTURE describes AXL surfaces in use without
adding new code.

## Up next

The remediation pass from the second-pass judge review is complete.
Remaining backlog: a `curl`-based smoke check for the Next.js
frontend file proxies, the in-orch-startup sentinel for the Anthropic
key (so the UI can show "host already configured"), the v2 MCP wiring
sketched in `refs/PLAN.md` §19c.
