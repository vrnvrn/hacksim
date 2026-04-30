# 47. Production env defaults committed for the Vercel build

## What changed

The Vercel build needs `NEXT_PUBLIC_USE_MOCKS=true` and a hosted-preview
marker to render the fixture page correctly. Without committed
`.env.production`, every fork would either ship empty values or require
dashboard configuration before the first build worked. Two new files
land:

- `apps/web/.env.production` (committed): Mode V1 defaults. Mocks on,
  orchestrator URL empty (unused while mocks are on), hosted-preview
  banner enabled.
- `apps/web/.env.production.example` (committed): the Mode V2 transition
  template. Mocks off, orchestrator URL pointed at the future Fly.io
  host, banner still on so the page is honest about being remote.

Files changed:

- `.gitignore` gains two exceptions (`!.env.production` and
  `!.env.production.example`) so the public defaults travel with the
  repo while `.env`, `.env.local`, and `.env.production.local` stay
  local.

## Why

The Next.js build embeds `NEXT_PUBLIC_*` vars at compile time. If those
vars are absent or wrong, the hero spin-up button hits the wrong route,
the live page snapshots fail to resolve, and the showcase modal renders
empty. Committing a `.env.production` with the V1 defaults is safe
because every value is a `NEXT_PUBLIC_` (no secrets) and reproducible
because forks build the same bundle Vercel would. Forks deploying with
a hosted orchestrator override the defaults in the Vercel dashboard;
dashboard env vars take precedence over the committed file.

## How to verify

```
cd apps/web && pnpm build
```

The build prerenders the static pages and registers the dynamic API
routes without errors. `grep NEXT_PUBLIC .env.production` shows the
three vars. `git ls-files apps/web/.env*` shows both the committed
file and the example.

## Gensyn surface used

None. Frontend env config only.

## Up next

Commit a `vercel.json` so the install and build commands are explicit
and the hosted build reads the same way across forks.
