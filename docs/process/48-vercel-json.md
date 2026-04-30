# 48. vercel.json so the hosted build is reproducible

## What changed

Vercel auto-detects Next.js from `apps/web/package.json`, but that
auto-detect path leaves the install command, build command, and output
directory implicit (defaulting to whatever the dashboard remembers).
For a fork to deploy without dashboard guesswork, those values need to
live in the repo.

Files added:

- `apps/web/vercel.json`: pins `framework=nextjs`,
  `installCommand=pnpm install --frozen-lockfile`,
  `buildCommand=pnpm build`, `outputDirectory=.next`,
  `trailingSlash=false`, `github.silent=true` (no auto deployment
  comment on every PR).

The Vercel project's "Root Directory" still needs to be set to
`apps/web` once in the dashboard; vercel.json has no key for that. The
deploy guide names the step.

## Why

A reproducible deploy means a fresh fork can `vercel link` and ship
without dashboard configuration beyond the one-time root-dir setting.
Committing the install and build commands also stops the dashboard
from being the single source of truth for what runs at build time;
anyone reviewing the deploy can read `vercel.json` and know exactly
what Vercel will execute.

`github.silent=true` keeps PR threads clean. The default Vercel bot
posts a deployment URL on every commit; for a personal fork that
volume of comments is noise.

## How to verify

```
cd apps/web && pnpm build
```

Confirms the install and build commands work. The Vercel CLI run
(`vercel --prod`) reads the same config and produces the same bundle.

## Gensyn surface used

None.

## Up next

Add the hosted-preview banner so judges hitting the deployed URL see
the page is fixtures, not a live AXL mesh.
