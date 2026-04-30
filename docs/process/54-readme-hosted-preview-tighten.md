# 54. README hosted-preview section tightened

## What changed

The README "Hosted preview" section pitched the hosted page as a
fixture-mode preview "with a hosted-orchestrator (Mode V2) deploy on
the roadmap." The submission shape is video plus repo, so the hosted
orchestrator does not need to ship at all; the hosted page is the
on-ramp, not the demo.

Files changed:

- `README.md`: rewrote the two-paragraph "Hosted preview" section.
  Reframes the hosted page as the on-ramp; names the layout-mounted
  banner and the per-page recorded-run pill as the honesty surfaces;
  points readers at `make demo` for the canonical experience and at
  `docs/ARCHITECTURE.md` for the message flow; mentions the hosted
  `/docs` "Run it locally" panel for the quickstart with timings and
  a verification block. Drops the "Mode V2 is on the roadmap"
  forward-looking line.

## Why

We are not promising what we are not building. A hackathon submission
that says "Mode V2 is on the roadmap" implies a commitment we have no
plans to honour for this submission, and a panel reading the README
chronologically would expect to see Mode V2 ship by the deadline.
Reframing the section as "the preview is a recording on purpose, the
real demo is local, the architecture supports public deploy if a fork
wants it" is honest about scope.

## How to verify

```
rg -n 'Mode V2|on the roadmap' README.md
```

No matches in the body. The remaining mention of Mode V2 is in
`docs/DEPLOY_VERCEL.md`, which describes the configuration override
path for forks; that file is opt-in reading.

## Gensyn surface used

None.

## Up next

Process notes for commits 51 to 54, plus an update to refs/PLAN.md
recording the Mode V2 parking decision.
