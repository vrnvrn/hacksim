# 50. Deploy-to-Vercel guide and README hosted-preview section

## What changed

The Vercel deploy needs a one-time dashboard configuration step
(Root Directory = `apps/web`) and a documented env-var matrix for
Mode V1 (fixtures) and Mode V2 (hosted orchestrator). Without that,
forks would have to read `vercel.json`, the env files, and the
HostedModeBanner source to figure out the wiring.

Files added:

- `docs/DEPLOY_VERCEL.md`: one-time setup, build settings, env vars,
  deploy command, verification checklist, and troubleshooting. The
  Mode V2 transition is captured as an "override these dashboard
  values" section so a future commit can flip the deploy without
  touching the doc.

Files changed:

- `README.md`: a new "Hosted preview" section between the architecture
  block and the status line. One paragraph naming what the Vercel
  build is (a fixture-mode preview, not a live mesh) and pointing at
  the deploy guide.

## Why

A panel reading the README should know in 30 seconds that there are
two ways to see HackSim: click the hosted URL (fixtures) or run
`make demo` locally (real mesh). Naming both reduces the chance a
reviewer scrolls past the hosted link assuming it must be the real
demo, or scrolls past `make demo` assuming the hosted preview must be
better. The deploy guide makes the Vercel setup reproducible from a
fresh fork without dashboard guesswork.

## How to verify

```
ls docs/DEPLOY_VERCEL.md
rg 'Hosted preview' README.md
```

Both files show. The README "Hosted preview" section links the deploy
guide; the deploy guide links back to `refs/PLAN.md` 19d for the full
plan.

A real `vercel --prod` run from `apps/web/` produces a deployment URL.
The HostedModeBanner from commit 49 renders on the hosted URL once
the env vars are picked up.

## Gensyn surface used

None.

## Up next

Mode V2 transition: build the orchestrator into a Docker image, ship
it to Fly.io, set the Vercel project env vars to point the frontend
at the hosted backend, and update the banner copy. Tracked under
`refs/PLAN.md` 19d "V2 transition checklist."
