# 32. ETHGlobal Open Agents 2026 framing and HackSim voice pass

## What changed

Rewrites every user-facing surface so the project reads as HackSim (our submission) running on Gensyn AXL (the underlying tech), with ETHGlobal Open Agents 2026 attribution made explicit. Removes any phrasing that paraphrased Gensyn's own marketing copy.

- `README.md`: ETHGlobal Open Agents 2026 attribution at the top, the primary repo link is `github.com/vrnvrn/hacksim`, and a new "What is Gensyn AXL" section explains AXL in our own words so a judge new to the tech learns it from us. A line clarifies HackSim is not affiliated with Gensyn.
- `apps/web/components/Nav.tsx`: `[ github ]` now points at `github.com/vrnvrn/hacksim` (was the upstream AXL repo by accident).
- `apps/web/components/Footer.tsx`: HackSim primary link is `github.com/vrnvrn/hacksim`. The "Built on" column credits Gensyn AXL, Claude Code, and ETHGlobal Open Agents 2026 with their canonical URLs.
- `apps/web/components/Footer.test.tsx`: asserts the HackSim link and the ETHGlobal credit. 64 vitest tests pass (one new).
- `apps/web/app/docs/page.tsx`: doc cards link to `vrnvrn/hacksim` canonical files (`ARCHITECTURE.md`, `AGENTS.md`, `docs/process/`). New "About AXL" panel introduces Gensyn's tech in our voice plus links to `docs.gensyn.ai/tech/agent-exchange-layer` and `github.com/gensyn-ai/axl` for readers who want the source.
- `apps/web/app/page.tsx`: above the H1 a small mono label now reads `[ hacksim · ETHGlobal Open Agents 2026 ]`. The subhead is tightened so the hero stays inside the fold.

Writing rules respected throughout: no em dashes, no rhetorical contrast structures, no co-author trailers.

## Why

Three reasons this needed to land before the judge review.

First, attribution. ETHGlobal Open Agents 2026 is the hackathon we built HackSim at, and that fact has to be visible from any single page a judge lands on. Burying it in the README is not enough.

Second, identity hygiene. HackSim and Gensyn AXL are two different projects. AXL is the Go binary that gives any application an encrypted peer-to-peer transport; HackSim is a hackathon simulator that happens to use AXL for cross-agent messaging. Conflating them in copy weakens both. The "About AXL" panel and the README section are written in our voice so neither team is misrepresented.

Third, plagiarism risk. An earlier draft had phrases that were too close to Gensyn's own docs. We rewrote those passages from scratch, kept all the technical claims, and linked out to Gensyn's canonical pages where readers should go for the source.

## How to verify

```
cd apps/web
bun run test                  # 64 vitest tests pass
bun run build                 # clean build, 0 warnings
```

Open the site:

- `http://localhost:3000`: hero label reads `[ hacksim · ETHGlobal Open Agents 2026 ]`.
- `http://localhost:3000/docs`: doc cards link to `vrnvrn/hacksim`. The About AXL panel describes AXL in our words and links to docs.gensyn.ai and the AXL repo.
- Footer on every page: HackSim repo link, ETHGlobal credit visible, Gensyn AXL and Claude Code credited under "Built on".

A targeted scan confirms the writing rules:

```
LC_ALL=C grep -rE '—|not just|Not only|Not just' README.md apps/web/app apps/web/components
```

No matches.

## Gensyn surface used

None new. The change is entirely textual and link-level. The AXL nodes, the orchestrator endpoints, and the role workers are unchanged.

## Up next

A live-page bug fix: the snapshot does not refresh after the initial server fetch and the SSE event parsing drops the envelope type. Both showed up while testing this commit on a real `make demo` run and are tracked under commit 33.
