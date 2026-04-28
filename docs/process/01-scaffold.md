# 01. Scaffold the repo

## What changed

Initialised the project skeleton. Added these files:

- `LICENSE`, MIT.
- `Makefile`, with top-level targets for build, test, demo, and hooks installation.
- `pyproject.toml`, defining the Python package, pytest configuration, and ruff configuration.
- `packages/__init__.py` and `tests/__init__.py`, the Python package roots.
- `tests/test_smoke.py`, a single passing test so `make test` exits zero.
- `scripts/hooks/pre-commit.sh` and `scripts/hooks/commit-msg.sh`, writing-rule enforcement.
- `.githooks/pre-commit` and `.githooks/commit-msg`, thin shims pointing at the scripts.

## Why

Two reasons.

The rest of the build assumes a Python package layout, a test runner that exits zero on success, and a Makefile that documents the contract. Without these in place, every later commit invents its own conventions. Locking the conventions on day one keeps the audit trail tidy.

The writing rules in `refs/PLAN.md` section 17 are best enforced by the version control system itself. The `pre-commit` hook scans the staged diff for em dashes, en dashes, and the two rhetorical contrast patterns we banned. The `commit-msg` hook scans the message for those plus co-author trailers and the "generated with" attribution. A single rejected commit is cheaper than a slipped-through one. The hook scripts construct their search patterns from hex escapes so the scripts do not trip on their own staging.

## How to verify

```
make test
make hooks-install
```

`make test` runs pytest and expects exit zero. `make hooks-install` is opt-in; it sets `core.hooksPath` to `.githooks` for this repo only. Once installed, any subsequent commit that introduces a forbidden pattern fails with a clear error.

## Gensyn surface used

None. Pure plumbing.

## Up next

Commit 02 writes the README skeleton in Gensyn's voice, with the AXL quickstart and a link to `docs.gensyn.ai/tech/agent-exchange-layer`. Real Gensyn content lands in commit 03 with the AXL submodule.
