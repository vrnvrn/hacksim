# 49. Hosted-preview banner so a fixture is never mistaken for a real mesh

## What changed

The Vercel build runs against fixtures: the hero "Spin up sim" button
and the example tiles all hit `/api/mocks/*`, the run log replays a
recorded ndjson, and the showcase modal renders three pre-baked demo
projects. A judge clicking into a "live" page on the hosted URL must
not assume those snapshots came from a real AXL mesh.

Files added:

- `apps/web/components/HostedModeBanner.tsx`: small notice card that
  renders only when both `NEXT_PUBLIC_HOSTED_PREVIEW=true` and
  `NEXT_PUBLIC_USE_MOCKS=true` are set. Tells the user the page is
  fixtures and points them at `make demo` for the real mesh, plus a
  repo link.
- `apps/web/components/HostedModeBanner.test.tsx`: four Vitest cases
  cover the (hosted, mocks) combinations: neither set, only mocks,
  only hosted, both set. The banner only renders in the both-true case.

Files changed:

- `apps/web/app/page.tsx`: imports and mounts the banner above the
  main hero section. Server-rendered, no client JS.

## Why

`refs/PLAN.md` 19d Mode V1 says the hosted preview must declare its
fixtures. The banner is the only difference between the same Next.js
build running locally (where neither env var is set) and running on
Vercel (where both are set in `apps/web/.env.production`). When Mode V2
ships, `NEXT_PUBLIC_USE_MOCKS=false` is set in the Vercel dashboard
override and the banner compiles out for that deploy because the mocks
clause becomes false.

## How to verify

```
cd apps/web && pnpm test HostedModeBanner
```

Four tests pass.

```
cd apps/web && pnpm build
```

Build clean (the banner reads env at module load, so it bakes the
right behaviour into the static page).

Manual: with `NEXT_PUBLIC_HOSTED_PREVIEW=true NEXT_PUBLIC_USE_MOCKS=true
pnpm dev`, the banner renders under the hero. With either var unset,
the banner does not render.

## Gensyn surface used

None.

## Up next

A deploy-to-Vercel guide so the one-time dashboard setup and the env
matrix are reproducible from the README.
