# 35. Plain-English live status banner answering 'what is happening now'

## What changed

Adds `NowHappening`, a server-rendered banner above the stat pills on the live page. It reads the snapshot and produces a one-sentence headline plus a one-sentence detail in plain English so a viewer who has never seen the simulation knows exactly what the agents are doing.

Examples by phase:

- Phase 0: "3 sponsor agents are drafting bounties." Detail explains bounties land on the mesh as `bounty.posted` envelopes.
- Phase 1: "8 builders are reading the bounties and forming teams." Detail mentions the skill-profile broadcast plus `team.formed`.
- Phase 2: "Builders are submitting (3 of 8 projects in)." Detail explains the orchestrator git-archives each submission and serves it under a strict CSP for the showcase iframe.
- Phase 3: "Judging in progress (12 of 24 scores in). 3 judges reviewing 8 submissions." Detail names the `verdict.published` broadcast.
- Phase 4: "Hackathon closed. 8 projects ranked." Detail invites the user to open the showcase.

The header now also shows projects and verdicts pills alongside agents and bounties so the rendered numbers always match what `NowHappening` describes. The View showcase link is more prominent in phase 4.

The banner is a Server Component. The existing `RefreshTicker` re-runs the parent every 2.5 s while phase < 4, so the banner stays current with no client polling logic.

While testing this commit we verified the real-code path end to end. A builder writes `index.html`, `app.js`, and `style.css` into its working tree, git-commits, and broadcasts `project.submitted` with the commit hash. The orchestrator runs `git archive --format=tar | tar -x` on the working tree at that commit into `sim-runs/{sim_id}/projects/{pid}/`. The `ProjectDemoModal` Code tab dynamically imports `shiki`'s `codeToHtml` and renders the real source. The Demo tab iframe loads the real `index.html` from the orchestrator's static route under a strict CSP. No stubs, no fakes.

65 vitest tests pass. Build clean.

## Why

The user feedback after watching commit 34's run: "I can see numbers changing but I do not know what the agents are doing." Stat pills carry signal for someone who already knows the model; for a new viewer they read as noise.

The phase model already exists (0 designing, 1 forming teams, 2 building, 3 judging, 4 closed). What was missing was a sentence that translates the current snapshot into a concrete claim about agent behaviour. A small server component that pattern-matches on `phase` plus a couple of counters does the job, and it stays a Server Component because the snapshot is already on the server; pulling state to the client to render a sentence would have added complexity without changing the answer.

Showing projects and verdicts pills alongside agents and bounties also closes a small mismatch: `NowHappening` was citing numbers the header did not surface, so a curious viewer could not double-check.

## How to verify

```
cd apps/web
bun run test                  # 65 vitest tests pass
bun run build                 # clean
```

End-to-end:

```
make demo
```

Open `http://localhost:3000`, click Spin up sim, watch the banner shift through five distinct messages over the run. Read each one and confirm it says something a layperson would understand without prior context. Open the showcase from phase 4, confirm projects render in the iframe and the Code tab shows real source.

To prove the project source is real and not stubbed, after a run completes:

```
ls sim-runs/sim_*/projects/proj_*
git log sim-runs/sim_*/projects/proj_*/.git
```

You will see `index.html`, `app.js`, `style.css` plus the builder's commit history.

## Gensyn surface used

None new. The banner reads the snapshot the orchestrator already maintains (see commit 25). The end-to-end verification touches the same AXL surfaces the rest of the system uses: the role workers broadcast `project.submitted` over `/send`, the orchestrator listens via `/recv`, and the artefact pipeline turns the commit hash into a static-served bundle.

## Up next

A FAQ on the docs page covering the questions a Gensyn judge or ETHGlobal reviewer is likely to ask before reading any code. Tracked under commit 36.
