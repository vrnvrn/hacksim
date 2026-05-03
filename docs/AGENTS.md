# Agents

One page per role. Each role runs as a Python worker under the orchestrator's `Spawner`. The worker imports the `hacksim_network` skill module directly and uses the runtime in `packages/agents/_runtime.py` for the drain loop, dedupe, fanout, and gossip. Each role also ships a `CLAUDE.md` persona file you can read end to end; the file below quotes the opening of that persona and links to the rest.

## Organiser

**Persona:** `packages/agents/organiser/CLAUDE.md`. The organiser is the bootstrap node. Every other role peers through it, so it has the cleanest view of the mesh. It does not score projects, sponsor bounties, or write code; it keeps time.

**Code:** `packages/agents/organiser/role.py`, `packages/agents/organiser/decisions.py`.

**Phase ticks (quick pace):**

| Time | Envelope | Phase enum |
|---|---|---|
| t + 5 s  | `phase.tick` | `BOUNTY_DESIGN` |
| t + 18 s | `phase.tick` | `TEAM_FORMATION` |
| t + 30 s | `phase.tick` | `BUILD` |
| t + 75 s | `phase.tick` | `JUDGING` |
| t + 110 s | `hackathon.closed` (carries the leaderboard) | `SHOWCASE` |

**Inbound envelopes:** `verdict.published` (used to compute the final leaderboard before `hackathon.closed`).

**Outbound envelopes:** `phase.tick`, `hackathon.closed`. Both fan out via `WorkerState.fanout` so peers whose Yggdrasil tree had not converged on the first broadcast still receive the tick on retry.

## Bounty designer

**Persona:** `packages/agents/bounty_designer/CLAUDE.md`. Each designer is one of the sponsors at the hackathon, with a name and an opinion. The peer id picks one of eight archetypes (FoldLab, Helix Capital, DeepProtein, NorthStar, Lumen, Atlas Security, Vector, Drift). Each designer composes one bounty, posts it, and goes quiet.

**Code:** `packages/agents/bounty_designer/role.py`, `packages/agents/bounty_designer/decisions.py`.

**Inbound envelopes:** `phase.tick`. The designer waits for `BOUNTY_DESIGN` before composing.

**Outbound envelopes:** `bounty.posted`. The payload carries the sponsor name, the niche, the qualification list, and a budget. The runtime broadcasts on phase entry and re-broadcasts on later peer joins.

**Decision module:** with `ANTHROPIC_API_KEY` set, the bounty body attempts a Claude haiku 4.5 call (max_tokens 512) with the persona and prompt as context. Without a key, or on per-call SDK failure (rate limit, timeout), a deterministic stub keyed off the prompt hash and the designer's peer id picks a sponsor archetype and a qualification list from a curated table. SDK failures surface on the SSE stream as `decision.anthropic_failed`. Both paths emit the same envelope shape.

## Builder

**Persona:** `packages/agents/builder/CLAUDE.md`. Each builder has a skill profile (three to four skills) derived from its peer id, so no two builders look alike. Builders read the bounties, pick the one that fits, write a single-page web project, and submit.

**Code:** `packages/agents/builder/role.py`, `packages/agents/builder/decisions.py`, `packages/agents/builder/build.py`.

**Inbound envelopes:** `bounty.posted`, `phase.tick`. Bounties come in during `BOUNTY_DESIGN`; the builder stashes them and acts when the phase advances to `TEAM_FORMATION` and then `BUILD`.

**Outbound envelopes:**

- `team.formed` (carries `team_id`, `bounty_id`, `members`).
- `project.submitted` (carries `project_id`, `team_id`, `bounty_id`, `title`, `tagline`, `commit_hash`, `entry_path`, `working_dir`).

**Artefact pipeline:** the builder runs `git init && git add && git commit -m "..."` in its working directory, then broadcasts `project.submitted`. It also `POST`s artefact metadata to the orchestrator over a separate HTTP channel so the orchestrator can `git archive` the tree and serve it under a strict CSP for the showcase iframe. That second channel is filesystem registration, not agent control. Phase ticks, bounties, team formation, and project submissions all ride AXL.

**Decision module:** with `ANTHROPIC_API_KEY` set, the builder composes the project HTML with Claude (max_tokens 4096; the prompt asks for a compact ~2-3 KB demo). Without a key, or on per-call SDK failure (rate limit, timeout, mid-stream truncation), a deterministic template keyed off the bounty and the builder's peer id produces a working interactive `index.html`. SDK failures surface on the SSE stream as `decision.anthropic_failed` or `decision.anthropic_truncated`. Both paths produce a real, runnable project.

## Judge

**Persona:** `packages/agents/judge/CLAUDE.md`. Each judge has an archetype derived from its peer id (encouraging, balanced, strict, contrarian). The archetype sets the weights on a fixed five-criterion rubric (novelty, fit-to-bounty, technical depth, demo quality, documentation), each scored 0 to 10. Weights vary; criteria are constant so totals are comparable.

**Code:** `packages/agents/judge/role.py`, `packages/agents/judge/decisions.py`.

**Inbound envelopes:** `project.submitted`, `phase.tick`. Projects accumulate during `BUILD`; the judge acts when the phase advances to `JUDGING`.

**Outbound envelopes:**

- `rubric.published` once per judge (carries the archetype's weights so reviewers can audit how the judge scored).
- `verdict.published` once per (judge, project) pair (carries per-criterion scores, the weighted total, and one paragraph of feedback).

**How judges read project files:** judges read submitted artefacts directly from the filesystem path the orchestrator registered when the builder broadcast `project.submitted`. There is no Playwright sandbox in this submission. (An earlier README claim said there was; it has been removed. Hands-on evaluation is on the v2 list.)

**Decision module:** with `ANTHROPIC_API_KEY` set, the judge writes the per-project feedback paragraph with Claude (max_tokens 512) using the rubric and the project file contents as context. Without a key, or on per-call SDK failure (rate limit, timeout), a deterministic stub keyed off the archetype, the project, and the judge's peer id produces five scores plus a feedback paragraph that varies by archetype. SDK failures surface on the SSE stream as `decision.anthropic_failed`. Both paths emit the same envelope shape.

## Where to verify

| What | Where |
|---|---|
| Real two-node AXL exchange | `tests/integration/test_two_node_send.py` |
| Per-role unit tests | `packages/agents/<role>/tests/` |
| Snapshot accumulator end-to-end | `packages/orchestrator/tests/test_snapshot.py` |
| Headless full-stack smoke | `make smoke` (runs `scripts/smoke_e2e.py`) |
| Browser smoke | `make demo` then click into the live page and the showcase modal |
