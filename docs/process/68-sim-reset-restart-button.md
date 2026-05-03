# 68. POST /api/sim/reset and the in-UI Restart button

## What changed

A wedged sim has historically been recoverable only by dropping to a
terminal and running `pkill -f third_party/axl/node`. That is not
acceptable on a public hosted demo, and even on a local demo a judge
mid-presentation should not have to leave the browser.

This commit ships a recovery path that lives entirely in the UI.

**Backend.** New endpoint `POST /api/sim/reset` in
`packages/orchestrator/api.py`. Idempotent. Stops every controller in
`app.state.controllers` concurrently via `SimController.stop_fast`
(the SIGKILL helper added in process note 66), each capped at 2.5
seconds via `asyncio.wait_for`. Clears `app.state.controllers`.
Returns 204 on success regardless of whether any controllers were
running. Errors raised by individual stops are swallowed so one
broken controller cannot prevent the others from being cleaned up.

**Frontend proxy.** New `apps/web/app/api/sim/reset/route.ts`. POST
forwards to the FastAPI orchestrator at `ORCHESTRATOR_BASE_URL`. In
mock mode (`NEXT_PUBLIC_USE_MOCKS=true`) returns 204 immediately.

**Restart button.** New client component
`apps/web/components/RestartSimButton.tsx`. Pops a confirm dialog
("Stop this simulation and every other running sim, then return to
the home page?"). On confirm, calls the proxy and redirects to `/`.
Surfaces non-2xx as an inline error.

**Wired into the live page.** `apps/web/app/sim/[id]/page.tsx` imports
the component and drops it into the existing pill row in the header,
flush right via `ml-auto` so it sits opposite the back-to-home link
without disturbing the existing pills.

## Why

The reset endpoint reuses the fast-stop path from process note 66, so
the Restart button has the same wall-time guarantee as the new sim
spawn: under three seconds in the typical case, capped at 2.5
seconds per controller via `asyncio.wait_for`. The pre-confirm step
is intentional: a single click should not be able to stop a running
demo for everyone watching.

The endpoint is unauthenticated. For the local demo this is fine:
the orchestrator binds 127.0.0.1 only. For a hosted Fly deploy a
follow-up could gate it behind a header or a session cookie, but the
hackathon-day demo is single-tenant by design (per `refs/PLAN.md`
§19) so any visitor calling reset is at most a denial-of-service
against themselves.

## How to verify

- `pytest packages/orchestrator/tests/test_api.py -q` reports 20
  passed (was 17, plus three new in `TestReset`).
- `pnpm vitest --run` reports 94 passed across 27 files (HeroPrompt 8,
  RestartSimButton 4 new).
- `npx tsc --noEmit` is clean.
- Manual: `make demo`, type a prompt, hit Spin up sim, wait for the
  redirect. Click the Restart button in the live page header.
  Confirm the dialog. Within ~3 seconds the page redirects to `/` and
  every AXL Go binary is gone (verify with `pgrep -f third_party/axl`
  returning nothing).

## Gensyn surface used

None directly. The reset endpoint stops processes that own AXL
nodes; the AXL HTTP API at `127.0.0.1:9002` is not called.

## Up next

Closes the three-fix sequence in `refs/UI_FIXES_PLAN.md`. Open
follow-ups for after the hackathon: a hosted-mode auth gate on the
reset endpoint, and a per-user sim namespace so reset is scoped to
the caller's session rather than every running sim.

## Files

`packages/orchestrator/api.py`,
`packages/orchestrator/tests/test_api.py`,
`apps/web/app/api/sim/reset/route.ts`,
`apps/web/components/RestartSimButton.tsx`,
`apps/web/components/RestartSimButton.test.tsx`,
`apps/web/app/sim/[id]/page.tsx`,
`docs/process/68-sim-reset-restart-button.md`.
