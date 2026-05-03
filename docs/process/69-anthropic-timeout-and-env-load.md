# 69. Disable Anthropic SDK retry, raise compose timeout, autoload .env

## What changed

Three small fixes that were sitting in the working tree before the
demo readiness audit and never committed. They land together because
they all govern whether `make demo` produces real Claude-backed
output or silently falls back to the deterministic stub.

**`packages/agents/_anthropic.py`.** The shared `make_client` helper
now passes `max_retries=0` to `anthropic.Anthropic(...)`. The SDK
defaults to two internal retries on every call. Combined with our own
single retry path in `call_with_retry`, a slow compose retried three
times by the SDK plus once by our wrapper expanded a 60-second wall
budget into roughly three minutes, well past the BUILD phase
deadline. Disabling the SDK loop makes `call_with_retry` the only
retry path.

**`packages/agents/builder/build.py`.** The compose call passes
`timeout=60.0` to `make_client`. The previous default of 10 seconds
aborted nearly every compose mid-stream because Claude haiku 4.5
reliably takes 15 to 30 seconds to produce 8 KB of HTML/CSS/JS. With
the timeout raised, real LLM-generated single-page projects make it
into the showcase iframe instead of the deterministic stub.

**`scripts/run_demo.sh` plus a new `.env.example`.** The script now
sources `.env` at boot if present, with `set -a` so every variable
becomes an exported env var for child processes. `.env.example`
documents the keys we read: `ANTHROPIC_API_KEY`, `HACKSIM_MODEL`,
`HACKSIM_PACE`. The user copies `.env.example` to `.env` and fills
in the key once; subsequent `make demo` runs no longer need an
`export` step.

## Why these belong together

All three were demo-blocking on a fresh checkout: a contributor with
an Anthropic key in their shell still hit a triple-retry timeout
storm and ended up with deterministic output. With these landed, the
single-shot 60-second budget per compose call is honoured and the
key flows from `.env` automatically.

The readiness audit at `refs/DEMO_READINESS.md` §B3 flags these
explicitly as the blocker for any reviewer cloning the repo today.

## How to verify

- `pytest packages/agents/ -q` reports unchanged pass count (the
  retry knob does not change behaviour when no exception fires).
- Manual: `cp .env.example .env`, edit to add the key, `make demo`,
  watch the run log on `/sim/<id>`. The builder.compose calls should
  emit `decision.anthropic_succeeded` events not
  `decision.anthropic_failed` from timeout. Project HTML in the
  showcase iframe should be visibly distinct per builder.

## Gensyn surface used

None directly. All three changes govern the Anthropic call path that
runs inside each role process before any AXL traffic.

## Up next

Judge retry on empty state.projects to close the smoke-pace race.
See `refs/DEMO_READINESS.md` §B2 and the next process note.

## Files

`packages/agents/_anthropic.py`,
`packages/agents/builder/build.py`,
`scripts/run_demo.sh`,
`.env.example`,
`docs/process/69-anthropic-timeout-and-env-load.md`.
