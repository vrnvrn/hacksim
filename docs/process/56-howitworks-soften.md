# 56. Soften the HowItWorks third-card claim

## What changed

The third card on the home page used to read:

> Live feed of every message between agents on a real AXL mesh. Click
> any winner and play with what they built.

On the hosted preview, the page replays a recorded run; "Live feed"
in present tense paired with "real AXL mesh" needed the layout banner
to walk it back. Reworded to a neutral statement true on both
surfaces:

> Watch agents talk peer-to-peer over an AXL mesh and click any
> winner to play with what they built.

The architecture claim ("AXL mesh", "peer-to-peer") is still there
because it is true: HackSim runs on AXL when the demo runs locally,
and the recording was produced on a real AXL mesh too. What is gone
is the present-tense "Live feed" framing that conflicted with the
hosted preview's recorded shape.

Files changed:

- `apps/web/components/HowItWorks.tsx`: third card body rewritten.
- `apps/web/components/__snapshots__/HowItWorks.test.tsx.snap`:
  vitest snapshot regenerated.

## Why

The hosted-preview banner does the heavy lifting on page-level
honesty (every page now declares the recorded-run nature). Marketing
copy that the banner has to walk back is a tax on the reader. A
neutral verb ("Watch") plus the architectural fact ("AXL mesh,
peer-to-peer") is true in both contexts and lets the banner do its
own job rather than retro-fixing the home page.

## How to verify

```
cd apps/web && pnpm test HowItWorks
```

Three tests pass; one snapshot updated.

```
cd apps/web && pnpm test
```

Full suite, 77 tests pass.

## Gensyn surface used

None.

## Up next

Update the commit log with entries 47-58 and call this honesty pass
complete. Future copy changes go through the same gate: every claim
on the hosted preview reads the same way as it does locally, or the
banner explains the difference.
