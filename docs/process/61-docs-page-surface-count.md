# 61. /docs Architecture card surface count to four

## What changed

The Architecture card on `/docs` (the small grid of three pointers above the
FAQ) said:

> Includes the message-flow diagram and the three AXL surfaces HackSim
> exercises (topology, send, recv).

Updated to four, with `mcp` named in the same parenthetical so a reader
clicking through to `docs/ARCHITECTURE.md` is not mid-paragraph contradicted.

## Why this needed its own commit

Same family of drift as commit 55 (FAQ entry), different surface. Caught
during the 2026-05-02 reality audit (`refs/REALITY_AUDIT_2026-05-02.md` D2).

## Verify

- `pnpm vitest --run` reports 80/80 web tests passing.
- `npx tsc --noEmit` is clean.

## Files

`apps/web/app/docs/page.tsx`.
