# 64. Centralise the Anthropic model id in `packages/agents/_anthropic.py`

## What changed

Four decision sites each had their own copy of:

```python
model=os.environ.get("HACKSIM_MODEL", "claude-haiku-4-5-20251001")
```

A model refresh (when Anthropic ships a successor) used to be four edits in
four files. The reality audit
(`refs/REALITY_AUDIT_2026-05-02.md` D7) flagged the duplication as a
production risk: a missed site silently keeps the old model.

Now there is one source of truth in
`packages/agents/_anthropic.py`:

```python
DEFAULT_MODEL = "claude-haiku-4-5-20251001"

def get_model() -> str:
    return os.environ.get("HACKSIM_MODEL", DEFAULT_MODEL)
```

Each call site imports `get_model` from `_anthropic` and uses
`model=get_model()`. The `HACKSIM_MODEL` env var override behaviour is
unchanged. `os` imports stay where they are because `ANTHROPIC_API_KEY`
lookup still uses them.

## Why this needed its own commit

A model refresh is operationally routine; the structure should make it a
one-line edit. Centralising before a refresh is needed (rather than after a
silent miss) is the cheap fix.

## Verify

`pytest packages/agents/ -q` reports 105 passed. No behaviour change; the
default model id and the env override are byte-for-byte identical. The
existing Anthropic-fallback tests cover both retryable and non-retryable
error paths and continue to pass.

## Files

`packages/agents/_anthropic.py`,
`packages/agents/bounty_designer/decisions.py`,
`packages/agents/builder/decisions.py`,
`packages/agents/builder/build.py`,
`packages/agents/judge/decisions.py`.
