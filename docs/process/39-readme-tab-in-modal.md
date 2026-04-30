# 39. README tab separate from the demo

## What changed

`ProjectDemoModal` gains a dedicated README tab that renders
`README.md` when the project ships one. The Demo tab stays pinned to
the project's true entry file (`index.html` or whatever the builder
named in `entry_path` on `project.submitted`) so reviewers can
distinguish "what the project actually does interactively" from "what
the agents wrote about it."

Files changed:

- `apps/web/components/ProjectDemoModal.tsx`: tab list grows to four
  (Demo, Code, README, Verdict). README is hidden when the project
  has no `README.md` in the file list. The renderer is the same
  `shiki.codeToHtml` path as the Code tab, with markdown highlighting.
- `apps/web/components/ProjectDemoModal.test.tsx`: existing tests pass
  unchanged; the snapshot is regenerated to include the new tab.
- `apps/web/components/__snapshots__/ProjectDemoModal.test.tsx.snap`:
  regenerated.

## Why

Builders sometimes write a small README alongside the artefact. Before
this commit the Demo tab swapped to `README.md` if `entry_path`
pointed there, which made the same tab change semantics across
projects. Splitting README into its own tab keeps Demo deterministic
(always the interactive entry) and gives README its own home.

## How to verify

```
cd apps/web && pnpm test -- -u ProjectDemoModal.test.tsx
```

Four tests pass; one snapshot updated. Manual smoke: open a winner
with `README.md` present; Demo stays interactive, README shows in its
own tab. On a project without a README, the README tab is hidden.

## Gensyn surface used

None. Frontend-only change.

## Up next

Surface project-level metadata (LICENSE, package.json, importmap)
through dedicated tabs as it ships. Each new tab follows the same
shape: presence-gated, shiki-rendered, separate from Demo.
