# 38. Code tab raw file proxy and font hardening

## What changed

The showcase modal Code tab loaded a file list from
`/api/sim/{id}/projects/{pid}/files` and then tried to fetch each file
body from `/api/sim/{id}/projects/{pid}/files/{path}`. Under
`pnpm dev` the second route had no Next.js proxy, so individual file
fetches returned 404, the modal silently cleared the buffer, and
`SourceView` rendered "1 lines" on an empty string. Mock mode masked
the regression because `apps/web/app/api/mocks/projects/[pid]/files/[...path]`
already existed.

Files added:

- `apps/web/app/api/sim/[id]/projects/[pid]/files/[...path]/route.ts`:
  forwards raw file bytes from FastAPI `read_project_file` so the Code
  tab can read individual files under `pnpm dev`.

Files changed:

- `apps/web/components/ProjectDemoModal.tsx`: surfaces a `contentError`
  alert when a file fetch fails instead of silently rendering an empty
  pane.
- `apps/web/app/fonts.ts`, `apps/web/app/globals.css`: dropped the
  unshipped General Sans local-font fallback that was producing
  repeated 404s in the dev server logs. Display typography stays on
  Inter Variable.

## Why

A judge clicking into the Code tab on a real submission would see a
blank pane reading "1 lines" with no error, no clue, and no recourse.
The artefact, the leaderboard, and the Demo iframe were all real; the
Code tab regression was a frontend proxy gap, not placeholder scoring.
Surfacing fetch errors plus the missing route together restores Code
tab parity with the Demo tab. The font fix removes ~50 console 404s
per session that had nothing to do with the bug but were noisy.

## How to verify

```
cd apps/web && pnpm test ProjectDemoModal.test.tsx
```

Four tests pass. With `make demo` running, click any winner card,
switch to Code, click `index.html`. The buffer renders, line count is
the actual line count, and `style.css` and `app.js` load on click. If
the orchestrator returns an error, the alert renders the HTTP status.

## Gensyn surface used

None. The fix is entirely on the Next.js proxy side; AXL traffic is
unchanged.

## Up next

Add a `curl`-based smoke line that checks `.../files/index.html` over
the live proxy alongside the existing iframe smoke, so a future Next
proxy gap fails CI instead of failing in front of a judge.
