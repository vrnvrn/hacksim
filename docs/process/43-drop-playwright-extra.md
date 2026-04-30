# 43. Drop the unused Playwright extra and rewrite the judge sentence

## What changed

The `agents` pip extra in `pyproject.toml` declared `playwright>=1.40`,
but no Python file under `packages/` ever imported it. The README told
judges they "optionally interact via a Playwright browser" but no
Python worker ever spawned a browser; no `from playwright` import
exists in the agent stack. Both go.

Files changed:

- `pyproject.toml`: removes the `agents` extra block entirely. The
  rest of the optional-dependency table (`dev`, `orchestrator`) is
  unchanged.
- `scripts/run_demo.sh`: the bootstrap install hint goes from
  `pip install -e .[dev,orchestrator,agents]` to
  `pip install -e .[dev,orchestrator]` since `agents` no longer
  exists.
- `README.md`: the judge bullet under "What HackSim does" goes from
  "scores every project, optionally interacting with the running demo
  via a Playwright browser" to "writes its own rubric, reads the
  submitted project files, and scores every project against that
  rubric." The architecture section sentence "Judges also own a
  Playwright sandbox for hands-on evaluation" goes to "Judges read
  those artefacts directly from the filesystem to score them."

The frontend Playwright suite under `apps/web/tests/playwright/` is
unrelated to this commit and unchanged.

## Why

A claim that ships in the README but is contradicted by ripgrep is
worse than a missing feature. Removing the extra also drops a 200MB
browser bundle out of every install of the agents stack, because pip
extras pull their full transitive set on `pip install -e .[agents]`.
The remediation is symmetric: the extra is gone, the README sentence
is gone, the architecture description is honest. If we add a real
Playwright-based judge in v2 we add the import, the dep, and the
sentence at the same commit.

## How to verify

```
python -m venv /tmp/hacksim-fresh
/tmp/hacksim-fresh/bin/pip install -e ".[dev,orchestrator]"
/tmp/hacksim-fresh/bin/pip list | grep -i playwright
```

The third command produces no output. The previous install would have
listed `playwright 1.x` and `playwright-firefox`, etc.

```
rg playwright packages --glob '*.py'
```

Returns no matches.

## Gensyn surface used

None.

## Up next

The README "How HackSim uses AXL" surface count and the `Faq.tsx`
surface count both still claim MCP. That is the next remediation in
order.
