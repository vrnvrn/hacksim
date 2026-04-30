# 51. Hosted-preview banner in the root layout

## What changed

The HostedModeBanner used to mount only on the home page, so a judge
clicking from `/` to `/sim/[id]` lost the recorded-run notice the
moment they navigated. Moving the mount to `apps/web/app/layout.tsx`
inherits the banner on every route. Per-page mounts are removed so
the banner does not double-render.

Files changed:

- `apps/web/app/layout.tsx`: imports `HostedModeBanner` and renders it
  inside the body, before children, above the per-page Nav.
- `apps/web/app/page.tsx`: drops the per-page banner mount.
- `apps/web/components/HostedModeBanner.tsx`: copy is tighter and the
  shape is a horizontal strip rather than a card so it lives at the
  very top of the viewport without crowding the hero. New right-side
  links: "Run it locally" anchors at `/docs#run-it-locally`, "Repo"
  points at the GitHub mirror.
- `apps/web/components/HostedModeBanner.test.tsx`: existing four cases
  rewritten for the new copy and the new link labels.

## Why

A page-level mount cannot defend against navigation. The Vercel build
is one URL with multiple routes; honesty has to follow the user. Root
layout is the right scope: render the banner once, every route gets
it. The thin-strip shape is a convention judges recognise from many
SaaS dashboards (Slack, Linear, Stripe all use it for "you are using
the demo / staging / preview" notices), so the visual idiom is doing
work for us.

## How to verify

```
cd apps/web && pnpm test HostedModeBanner
```

Four cases pass.

```
cd apps/web && pnpm build
```

Build clean.

Manual: with `NEXT_PUBLIC_HOSTED_PREVIEW=true NEXT_PUBLIC_USE_MOCKS=true
pnpm dev`, navigate to `/`, `/examples`, `/docs`, `/sim/<canned-id>`,
`/sim/<canned-id>/showcase`. Banner appears at the top of every page
with the "[ hosted preview ]" tag and the Run-it-locally and Repo
links.

## Gensyn surface used

None.

## Up next

Add a date-stamped "recorded run" pill to the live and showcase
headers so a fixture replay cannot be confused for a live mesh on the
pages where StatPills and NowHappening are most visible.
