# 59. Audit P3 pass: cosmetic and edge polish

## What changed

P3 closes out the audit with the cosmetic and edge-case items.
Mostly copy and visual tweaks; one file rename (FaqExpandAll into its
own client island), one new schema field (snapshot_version), and one
keyboard shortcut.

- **P3-1.** NowHappening banner stops embedding StatPill numbers in
  its headlines, so the live page header does not double up the same
  counts on adjacent lines.
- **P3-2.** README and RunItLocally panel say "two to five minutes"
  for `make demo` instead of an unconditional "five minutes" so the
  range matches reality (clean clone vs make-build-axl already done).
- **P3-3.** FAQ "Was this built during the hackathon?" answer
  generalises away the stale "35+ commits" figure to "every commit
  during the window".
- **P3-4.** Demo iframe Info banner enumerates each disabled
  capability ("scripts and styles only. No network, no forms, no
  cookies, no top-level navigation") so the sandbox guarantee is
  precise.
- **P3-5.** SourceView line-count fallback returns 0 on empty content
  instead of "1 lines" (the original showcase regression we already
  fixed surface-level via contentError; this is the defence-in-depth
  layer).
- **P3-6.** `_new_sim_id` uses `secrets.token_hex(4)` (8 hex chars,
  4B ids) instead of token_hex(3) so the birthday-collision threshold
  pushes from ~4k to ~65k sims.
- **P3-7.** Snapshot dict gains a `schema_version=1` field;
  apps/web/lib/types.ts adds an optional `schema_version` field on
  Snapshot plus a `SNAPSHOT_SCHEMA_VERSION` constant for forward
  drift detection.
- **P3-8.** FAQ "Do I need an Anthropic API key?" entry stops
  duplicating the deterministic-vs-Claude explanation and points up
  at "What AI are the agents using?" for the deep dive.
- **P3-9.** FAQ "What AI are the agents using?" lists four bullets
  to match the "Four call sites" lead-in (split builder bounty pick
  from builder HTML write so the count and structure agree).
- **P3-10.** ProjectDemoModal listens for `[` and `]` while open and
  cycles through Demo / Code / README / Verdict tabs without
  requiring a tab trigger to be focused. Tabs.Root flips to controlled
  mode (value + onValueChange) so the keyboard handler can drive
  state directly.
- **P3-11.** FAQ heading row gains a "[ expand / collapse all ]"
  control; first click opens every entry, second collapses all.
  Lives in apps/web/components/FaqExpandAll.tsx as a "use client"
  island so the FAQ body stays a server-rendered <details> tree.
- **P3-12.** RecordedRunPill drops to the muted-tone palette
  (`text-muted` on `bg-canvas`) so it sits visually flush with the
  StatPills it lives next to instead of shouting in accent purple.

## Why

P3 polish is the layer a reviewer notices in passing rather than in a
ripgrep audit. It removes paper-cut friction (copy that reads
double-counted, fallbacks that say "1 lines" on empty buffers, a
modal that requires clicking each tab trigger) and prepares the
schema for one of the few v2 tasks we can preemptively wire (the
snapshot version field).

## How to verify

```
.venv/bin/pytest packages/ tests/integration/ -q
cd apps/web && pnpm test
cd apps/web && pnpm exec tsc --noEmit
```

267 Python + 80 web tests pass; tsc clean.

Manual: open the FAQ on /docs and click "expand / collapse all" on
the heading row. Open a project modal and tap `]` to cycle tabs.
Reload `/sim/<id>` on a hosted-preview build; the RecordedRunPill
sits in the StatPill row in muted tone, not accent purple.

## Gensyn surface used

None.

## Up next

The remediation work driven by `refs/AUDIT_2026-04-30.md` is
complete. Three items are explicitly out of scope and noted in the
audit file: dark theme (Frontend #14), the dark-tone variant the
audit calls "RecordedRunPill colour audit" (P3-12, addressed above),
and any work that would require running `make demo` interactively to
record assets (e.g., the actual `tcpdump-demo.cast` recording the
asciinema slot points at). The next step is the Vercel push and the
second check-in submission.
