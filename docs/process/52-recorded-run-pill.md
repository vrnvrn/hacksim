# 52. Recorded-run pill on the live and showcase pages

## What changed

The hosted preview loads a fixture snapshot whose `created_at` reads
`2026-04-28T12:00:00Z`. Without a date marker on the live page header,
a visitor could read the StatPills, the PhasePill, and the NowHappening
banner as a real running mesh. The new pill surfaces the recording date
right next to the existing pills so the boundary is visible at the
page level, not just in the layout-mounted banner above the Nav.

Files added:

- `apps/web/components/RecordedRunPill.tsx`: gated by
  `NEXT_PUBLIC_HOSTED_PREVIEW=true` and `NEXT_PUBLIC_USE_MOCKS=true`
  (same gate as the banner). Reads `snapshot.created_at`, formats to
  `YYYY-MM-DD` without locale parsing so SSR and client agree, renders
  as `[ recorded YYYY-MM-DD ]` with a `status` role for screen readers.
  Falls back to the raw string if the date is malformed.
- `apps/web/components/RecordedRunPill.test.tsx`: four Vitest cases
  cover (no env vars), (hosted only), (both env vars), and the
  malformed-date fallback.

Files changed:

- `apps/web/app/sim/[id]/page.tsx`: imports the pill and mounts it
  next to the PhasePill in the header.
- `apps/web/app/sim/[id]/showcase/page.tsx`: mounts the pill in the
  StatPill row.

## Why

The layout banner is a thin strip across the top; once you scroll into
the page content, it is out of view. The pill is in-viewport on the
exact rows of the page that look most "live": the live page's
"X agents, Y bounties, Z projects, W verdicts" row, and the showcase
header's pool / submissions row. A judge cannot scroll past a fixture
without seeing it labelled.

## How to verify

```
cd apps/web && pnpm test RecordedRunPill
```

Four cases pass; full suite 73 tests green.

```
cd apps/web && pnpm exec tsc --noEmit
```

Type check clean.

Manual: with both env vars set, `/sim/<canned-id>` shows
`[ recorded 2026-04-28 ]` next to the PhasePill; the showcase page
shows it in the StatPill row. Without either env var, the pill is
absent.

## Gensyn surface used

None.

## Up next

The hosted-preview banner deep-links to `/docs#run-it-locally`. That
anchor still points at empty space; next commit lands the panel.
