# 67. HeroPrompt surfaces real spin-up errors with a 12-second timeout

## What changed

`apps/web/components/HeroPrompt.tsx` previously caught every failure
path of the `POST /api/sim` request as one generic message:

```
Could not reach the orchestrator. Run `make demo` and retry.
```

A 403 from the localhost-only Anthropic key check, a 500 from the
spawner, an unanswered request, or a real network outage all looked
identical. The user (or a judge mid-demo) had no way to tell which
path failed.

The new `spinUp` body wraps the fetch in an `AbortController` with a
12-second timeout, then dispatches the error to one of three message
shapes:

- **Non-2xx**: the message reads `Spin-up failed: POST /api/sim
  returned <status>: <body excerpt up to 200 chars>`. Whitespace in
  the body is collapsed so a JSON or HTML error renders on one line.
- **Abort (12s timeout)**: the message reads `Spin-up took longer
  than 12 seconds. The orchestrator may be cleaning up a prior sim.
  Try again.` This message complements process note 66 (the
  fast-stop fix that should keep this branch from firing).
- **Network failure (`Failed to fetch`)**: the original "Could not
  reach the orchestrator" hint stays.
- **Anything else**: the literal exception message preceded by
  `Spin-up failed: `.

Three new test cases cover the three branches. Each uses
`fireEvent` plus `vi.stubGlobal('fetch', ...)` and asserts on the
text content of the existing `role="alert"` element. Total HeroPrompt
test count moves from five to eight.

## Why

Two reasons:

1. The previous generic message hid real failures behind a
   misleading suggestion. A user who had the orchestrator running
   would re-run `make demo` for no reason, and a hosted demo where
   the orchestrator is reachable but spawned sims fail would
   surface the wrong diagnostic.
2. The 12-second timeout is a hard ceiling on the spin-up POST.
   Process note 66 caps the prior-controller fast-stop at 2.5
   seconds, plus a few seconds for the new spawner; total wall time
   should sit in the 4 to 7 second band. A 12-second wait is the
   point at which something is genuinely wrong. The button stays
   disabled while pending, so users cannot double-fire.

Tests use `fireEvent` rather than `userEvent` because
`userEvent.setup()` returns promise-based async helpers that conflict
with `useTransition`'s scheduler in React 19 under jsdom. The
existing tests on the controlled-by-parent path (`onSubmit` provided)
keep using `userEvent`; the new tests on the self-managed POST path
use `fireEvent` with a small `fillAndSubmit` helper.

## How to verify

- `pnpm vitest --run HeroPrompt` reports 8 passed in 1.3s.
- `pnpm vitest --run` reports 90 passed across 26 files.
- Manual: `make demo`, type a custom prompt, click Spin up sim. The
  redirect happens within ~5 seconds. Stop the orchestrator before
  clicking; the message reads "Could not reach the orchestrator".
  Restart, then patch the orchestrator to return 500 on `/api/sim`;
  the message reads "POST /api/sim returned 500" with the body
  excerpt.

## Gensyn surface used

None. The change is browser-side error UX.

## Up next

In-UI Restart button on the live sim page, backed by a new
`POST /api/sim/reset` endpoint. See `refs/UI_FIXES_PLAN.md` Fix 3.

## Files

`apps/web/components/HeroPrompt.tsx`,
`apps/web/components/HeroPrompt.test.tsx`,
`docs/process/67-hero-prompt-error-surface.md`.
