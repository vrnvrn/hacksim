# 60. FAQ surface count and MCP claim catch up to shipped code

## What changed

The FAQ on `/docs` had not caught up with the MCP round trip landing. Two
specific drift items, both visible to a reader of the home page:

1. The "How does HackSim use Gensyn AXL?" entry led with "Three AXL HTTP
   surfaces exercised by the running sim", followed by a paragraph that read
   "We do not exercise either [/mcp or /a2a] in this submission ... Wiring
   MCP-based judging is on the v2 list."
2. The same entry pointed forward at v2 work that had already shipped in
   commit `6caae9f`.

Both lines now match the running code: four AXL HTTP surfaces, MCP listed as
its own bullet with one sentence on what the organiser does with it during
JUDGING, A2A flagged as the surface we deliberately scoped out (with a pointer
to `docs/V2_MCP.md`).

## Why this needed its own commit

The drift was caught during the 2026-05-02 reality audit
(`refs/REALITY_AUDIT_2026-05-02.md` D1). README and `docs/ARCHITECTURE.md`
already say four surfaces; the home-page FAQ had not. A reader who lands on
the FAQ before the README will disbelieve the README.

## Verify

- `pnpm vitest --run` reports 80/80 web tests passing.
- `npx tsc --noEmit` is clean.
- Manually: open `/docs` locally, expand the AXL entry, confirm four
  bullets and no v2 reference.

## Files

`apps/web/components/Faq.tsx`.
