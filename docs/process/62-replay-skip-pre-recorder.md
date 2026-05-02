# 62. Replay listing explicitly hides pre-recorder sim directories

## What changed

The reality audit (`refs/REALITY_AUDIT_2026-05-02.md` D5) flagged that 12
`sim-runs/sim_2026-04-2{9,30}_*` directories from before the Recorder shipped
(commit 66) sit on disk without an `events.jsonl`. The concern was that they
might surface as broken entries in `GET /api/replay`.

Verified: they do not. The endpoint already filters on
`(child / "events.jsonl").is_file()`. The existing
`test_skips_directories_without_recording` covered the half-spawn case but not
the pre-recorder case explicitly.

This commit:

- Adds `test_skips_pre_recorder_sim_directories`, which constructs a sim
  directory with the exact shape we have on disk (role subdirs with `.log`
  and `.pem` files, a `projects/` tree, no `events.jsonl`) and asserts the
  listing hides it.
- Adds a docstring paragraph on the `/api/replay` endpoint pointing at that
  test, so a future reader investigating the same surface arrives at the
  regression directly instead of guessing whether the filter was deliberate.

No production code changes. The on-disk legacy directories stay; `make clean`
remains the documented way to remove them.

## Why this needed its own commit

Even though no behaviour changed, the audit promised verification. The test
plus the docstring lock the behaviour against future drift.

## Verify

`pytest packages/orchestrator/tests/test_replay_api.py -q` reports 9 passed.

## Files

`packages/orchestrator/api.py`,
`packages/orchestrator/tests/test_replay_api.py`.
