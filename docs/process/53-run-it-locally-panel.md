# 53. Run it locally panel on the docs page

## What changed

The hosted-preview banner deep-links to `/docs#run-it-locally`. The
new panel sits above the FAQ and gives a judge or visitor the
canonical recipe in one screenful.

Files added:

- `apps/web/components/RunItLocally.tsx`: three subsections.
  - **Quickstart.** Six-line shell snippet from `git clone` to
    `make demo`, plus the prereq list (Go 1.25+, Node 20 with pnpm,
    Python 3.10+, openssl) and an explicit "no API key required"
    note.
  - **What you should see.** Phase-by-phase timings keyed off the
    quick-pace defaults from `packages/agents/organiser/decisions.py`:
    t+0 boot, t+5 mesh peered, t+18 team formation, t+30 build, t+75
    judging, t+110 hackathon closed.
  - **Verify the qualification gate yourself.** Three commands the
    judge memo recommends panels run: `pytest
    tests/integration/test_two_node_send.py`, `tcpdump -i lo0` on
    port 9100, `ps aux | grep third_party/axl/node`.
- `apps/web/components/RunItLocally.test.tsx`: four Vitest cases
  cover the anchor id, the canonical commands, the verify commands,
  and the absolute github.com links.

Files changed:

- `apps/web/app/docs/page.tsx`: imports `RunItLocally` and mounts it
  between the three doc tiles and the FAQ. Same edit refreshes two
  stale tile descriptions (Architecture goes from "five-layer view"
  to "three AXL surfaces"; Agents drops the no-longer-shipped MCP
  tools language and now describes the deterministic-vs-Claude
  decision split).

## Why

The banner deep-link is a contract: judges click "Run it locally,"
they expect the recipe. Putting the panel on `/docs` means it lives
on the same page as the FAQ and the architecture pointers, so a
visitor can see the FAQ, the quickstart, the timings, and the
verification commands without leaving one route.

## How to verify

```
cd apps/web && pnpm test RunItLocally
```

Four cases pass; full suite 77 tests green.

Manual: open `/docs` on the hosted preview, scroll past the doc
tiles. The panel renders with the quickstart, the timings list, the
verify block, and the docs/process link.

## Gensyn surface used

None.

## Up next

Tighten the README "Hosted preview" section so the prose matches
what we just built and drop the Mode V2 "on the roadmap" forward
promise.
