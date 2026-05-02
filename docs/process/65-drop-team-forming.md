# 65. Drop the unused `team.forming` envelope type

## What changed

`team.forming` was declared in `packages/protocol/envelopes.py` (in both the
`EventType` Literal and `_KNOWN_EVENTS` frozenset) but no role ever emitted
it. The reality audit (`refs/REALITY_AUDIT_2026-05-02.md` D8) flagged it as
prototype scaffolding for a multi-builder team-formation flow that the
current submission does not exercise. Builders broadcast `team.formed`
directly as solo teams; there is no intermediate "forming" state.

Removed:

- `team.forming` from the `EventType` Literal in
  `packages/protocol/envelopes.py`.
- `team.forming` from the `_KNOWN_EVENTS` frozenset (same file).
- The example `"team.forming"` reference in the module docstring's wire
  shape.
- The corresponding parametrise case in
  `packages/protocol/tests/test_envelopes.py::TestIsKnownEvent::test_known_events`.
- The `"team.forming"` string from the SSE TYPES list in
  `apps/web/lib/use-sse.ts`.
- The synthetic `team.forming` line in
  `apps/web/lib/mocks/stream.ndjson` (commits between the two `team.formed`
  rows kept the timeline coherent).

Updated:

- `packages/agents/builder/role.py` module docstring: the parenthetical
  "solo team for now; multi-builder team formation is a stretch" reads
  "solo team (one builder per team). Multi-builder team formation is out
  of scope for this submission."
- `docs/ARCHITECTURE.md` line 49 and the autoresearch-delta table: envelope
  type count moves from eight to seven; the "team invites are wired in the
  wire protocol but not exercised yet" caveat is gone.
- `apps/web/components/Faq.tsx` autoresearch-delta paragraph: "eight
  envelope types" becomes "seven envelope types".

## Why this needed its own commit

The audit principle: scaffolding without behaviour is a maintenance trap.
A future contributor sees `team.forming` in the protocol, assumes it has a
purpose, and writes code against it. Deleting the unused declaration removes
that hazard and aligns the protocol surface with what the runtime actually
broadcasts.

## Verify

- `pytest packages/protocol/ packages/agents/ packages/orchestrator/tests/ -q`
  reports 261 passed.
- `pnpm vitest --run` reports 83/83 web tests pass.
- `npx tsc --noEmit` is clean.
- `rg 'team\.forming|team_forming' packages apps docs scripts` returns no
  matches in source code (the historical process note 13 is the only
  remaining reference, intentionally kept as a chronological record).

## Files

`packages/protocol/envelopes.py`,
`packages/protocol/tests/test_envelopes.py`,
`packages/agents/builder/role.py`,
`apps/web/lib/use-sse.ts`,
`apps/web/lib/mocks/stream.ndjson`,
`apps/web/components/Faq.tsx`,
`docs/ARCHITECTURE.md`.
