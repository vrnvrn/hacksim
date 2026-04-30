# Deploying HackSim to Vercel

This guide deploys the Next.js frontend at `apps/web` to Vercel. The orchestrator and the AXL Go binaries do not run on Vercel; that piece of HackSim runs locally with `make demo` or on a separate host (see `refs/PLAN.md` 19d Mode V2 for the planned Fly.io / Railway transition).

The default committed config produces **Mode V1**: a hosted preview that runs against fixtures. The hero spin-up button still works, the example tiles still navigate, the run log still replays, and the showcase modal still opens; everything resolves through `apps/web/app/api/mocks/*` instead of a live AXL mesh. The `HostedModeBanner` on the home page tells visitors the page is fixtures so a judge cannot mistake the snapshot for a real run.

## Prerequisites

- A Vercel account and the `vercel` CLI (`npm i -g vercel`).
- A clone of this repo with `git submodule update --init --recursive` already run (the Vercel build does not need the submodule, but `pnpm install` and a local `pnpm build` smoke test do).

## One-time project setup

From the repo root:

```bash
cd apps/web
vercel login
vercel link
```

When `vercel link` asks "Which scope?" pick your team or personal scope.
When it asks "Link to existing project?" choose **No**.
When it asks "What's your project's name?" use `hacksim` or your fork name.
When it asks "In which directory is your code located?" answer `./` (the link command runs inside `apps/web`, so `./` is the right answer).

Vercel auto-detects Next.js from `apps/web/package.json` and `apps/web/next.config.ts`. The committed `apps/web/vercel.json` pins `installCommand`, `buildCommand`, and `outputDirectory` so the build is reproducible across forks.

## Build settings (one-time, in the dashboard)

The `vercel.json` config file does not have a `rootDirectory` key. For monorepos with the app inside `apps/web/`, set Root Directory once in the project dashboard:

1. Open the project at `https://vercel.com/<scope>/<project>`.
2. Go to **Settings -> General -> Root Directory**.
3. Set to `apps/web`. Save.

After this the dashboard "Build & Output Settings" can stay on the defaults; `vercel.json` overrides them.

## Environment variables

The committed `apps/web/.env.production` already sets the Mode V1 defaults:

```
NEXT_PUBLIC_USE_MOCKS=true
ORCHESTRATOR_BASE_URL=
NEXT_PUBLIC_HOSTED_PREVIEW=true
```

Vercel picks these up automatically at build time (Next.js loads `.env.production` for `vercel build`). You do not need to set anything in the dashboard for Mode V1.

For **Mode V2** (hosted orchestrator), set in the dashboard under **Settings -> Environment Variables -> Production**:

```
NEXT_PUBLIC_USE_MOCKS=false
ORCHESTRATOR_BASE_URL=https://<your-orchestrator-host>
NEXT_PUBLIC_HOSTED_PREVIEW=true
```

Dashboard env vars override the committed `.env.production`. Redeploy after setting them.

## Deploy

From `apps/web`:

```bash
vercel --prod
```

The first deploy prints a `https://<project>-<hash>.vercel.app` URL. Once you wire a custom domain, that becomes the public link the README points at.

## Verifying the hosted preview

Open the deployed URL. You should see:

- A **[ hosted preview ]** banner under the hero, naming the fixtures and pointing at `make demo` and the repo.
- The hero **Spin up sim** button posts to the mocks route and lands on `/sim/sim_2026-04-28_a1b2c3` with the canned snapshot.
- Both the **HeroExamplesAside** preset cards and the **HeroExamples** grid spin up the same canned sim.
- The showcase modal **Demo**, **Code**, **README**, **Verdict** tabs all populate from the fixtures under `apps/web/lib/mocks/projects/`.

If the hosted-preview banner is missing, double-check that `NEXT_PUBLIC_HOSTED_PREVIEW=true` is set; that variable is the gate.

## What the hosted preview cannot show

- No real AXL mesh. The 15 AXL Go nodes do not run on Vercel.
- No live LLM calls. The Anthropic SDK call sites live in the orchestrator's role workers.
- No real artefact pipeline. The three projects under the modal are pre-baked under `apps/web/lib/mocks/projects/`; the orchestrator's `git archive` path is exercised by `make demo` only.

For all of those, point a reviewer at `make demo` or wait for Mode V2.

## Troubleshooting

**Build fails with "Cannot find module"**: confirm the dashboard Root Directory is `apps/web`, not the repo root. Vercel reads `pnpm-lock.yaml` and `package.json` from that directory.

**Hosted preview banner shows on local pnpm build**: by design. `.env.production` is loaded by `pnpm build` locally, and the banner reads those values at module load. If you want to test the production bundle without the banner, run `NEXT_PUBLIC_HOSTED_PREVIEW= pnpm build` instead.

**Hero spin-up errors "Could not reach the orchestrator"**: confirm `NEXT_PUBLIC_USE_MOCKS=true` on the build. Without mocks the frontend tries to hit `ORCHESTRATOR_BASE_URL`, and an empty value gives a network error.

**SSE never advances on hosted preview**: the mocks ndjson stream is finite. The run log shows the recorded events and stops. This is correct behaviour for Mode V1 fixtures.
