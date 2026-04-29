# 23. ProjectDemoModal with Demo, Code, Verdict tabs

## What changed

Built the centerpiece modal at `apps/web/components/ProjectDemoModal.tsx`.
Three tabs:

- **Demo**. Sandboxed iframe with `sandbox="allow-scripts"` (no
  `allow-same-origin`, no `allow-top-navigation`, no `allow-forms`, no
  `allow-popups`). A warning banner above the iframe spells out what the
  sandbox prevents. The iframe `src` points at the static artefact endpoint;
  the orchestrator (or the mock route in mock mode) returns the strict CSP.
- **Code**. Two-pane layout. `FileTree.tsx` on the left, `SourceView.tsx` on
  the right. The tree builds a folder hierarchy from a flat
  `ProjectFile[]`, expand-on-click, with the selected file highlighted. The
  source view dynamically imports `shiki` for syntax highlighting. Binary
  files render a placeholder; images render an inline preview block.
- **Verdict**. `VerdictPanel.tsx`. If the project has not been judged the
  panel shows an empty state. Once judged, it shows the rubric, a per-judge
  accordion, and a summary line ("Average: 7.4/10. Median: 7.5. Three
  judges scored.") that flags spread of opinion when the gap exceeds two
  points.

Three full mock projects ship under
`apps/web/lib/mocks/projects/{proj_d3vis, proj_threejs, proj_game}/static/`
with working `index.html`, `style.css`, and `app.js`:

- `proj_d3vis`: a D3 force-directed graph of every builder coloured by
  skill cluster. Drag nodes, hover for tooltips.
- `proj_threejs`: a three.js scene with six glowing columns arranged in a
  circle. Click a column to pulse, drag to orbit.
- `proj_game`: Permit Pong, two-paddle pong with a permit log on the right.
  WS for left paddle, arrows for right, first to ten wins.

## Why

The modal is the moment the simulation crosses from "watchable" to
"playable". A reviewer who reads no code can still feel the project is real:
the iframe is an actual web page running an actual builder's actual commit.
The strict CSP and the locked sandbox attributes make this safe by default.

Three projects exist so the modal proves it works against three different
shapes (vector graphics, WebGL, canvas-based game) and three different
runtime models (importmap-loaded D3, importmap-loaded three.js, no
dependencies). When the real backend lands, the only change to ship a real
project is dropping its files into the orchestrator's static mount.

## How to verify

```
cd apps/web
pnpm test components/ProjectDemoModal.test.tsx components/FileTree.test.tsx components/SourceView.test.tsx components/VerdictPanel.test.tsx
NEXT_PUBLIC_USE_MOCKS=true pnpm dev
```

Open `http://localhost:3000/sim/sim_2026-04-28_a1b2c3`. Scroll to
Submissions. Click "Try it" on any tile. The modal opens. Switch to the
Code tab; the file tree expands, click `app.js` to see syntax-highlighted
source. Switch to Verdict; the rubric and per-judge accordions render. Hit
Escape to close, click outside the modal to close, click the X to close.

## Gensyn surface used

Indirect. The modal consumes
`GET /api/sim/:id/projects/:pid/files` and
`GET /api/sim/:id/projects/:pid/static/<path>`. Both endpoints are served
by the orchestrator from `git archive` of the builder's working tree (see
`packages/orchestrator/artefacts.py`, commit 17). The strict CSP comes from
the orchestrator's static handler. In mock mode the dev route in
`apps/web/app/api/mocks/projects/[pid]/static/[...path]/route.ts` returns
the same headers.

## Up next

Commit 24 lands the showcase page at `/sim/[id]/showcase` with winner
ribbons (gold, silver, coral) and the Playwright smoke test that walks
hero, live, modal, and showcase.
