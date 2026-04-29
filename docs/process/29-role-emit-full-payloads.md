# 29. Role emits carry full envelope payloads

## What changed

Each agent role used to emit a small "diagnostic" payload to its stdout when broadcasting an envelope on the AXL mesh. That diagnostic payload was good enough for the run log but lacked the fields the orchestrator's snapshot accumulator (commit 25) needs to populate the live snapshot.

This commit splits each broadcast into two stdout events:

- `<envelope.type>` with the **full envelope payload**, suitable for the snapshot accumulator.
- `<envelope.type>.broadcast` with the diagnostic info (peer counts, re-broadcast schedule, archetype name) for the run log only.

Specifically:

- **bounty_designer**: `bounty.posted` now emits `{**payload, sponsor_peer_id}`. `bounty.broadcast` keeps the diagnostic.
- **builder**: `team.formed` now emits the full envelope payload (id, team_id, bounty_id, members, display_names, skills_summary). `project.submitted` now emits the full builder payload (commit_hash, entry_path, working_dir, files). Both keep their `*.broadcast` diagnostic counterparts.
- **judge**: `rubric.published` and `verdict.published` now emit the full envelope payloads (judge_peer_id, rubric, scores, total, feedback). Both keep their `*.broadcast` diagnostic counterparts.
- **organiser**: `phase.tick` now emits the phase payload directly so the snapshot's phase counter advances; `hackathon.closed` emits the full leaderboard. Both keep their existing `phase.tick.broadcast` and `hackathon.closed.broadcast` companions.

The 84 existing role unit tests remain green. The accumulator unit tests in commit 25 already covered the full-payload shape; this commit makes the emits match.

## Why

The orchestrator only sees what role workers write to stdout (commit 26 tails those logs). Cross-agent envelope payloads flow over the AXL mesh between role processes, but the orchestrator does not have its own AXL node, so the envelope-on-the-wire payload never reaches its snapshot. The fix is to also write the envelope payload to stdout, where the tailer can pick it up.

The before/after smoke against a real running orchestrator is the most direct way to see this work:

Before: at `t+85s` the snapshot showed `judges=0, verdicts=0` even though the leaderboard had 3 entries.

After: at `t+55s` the snapshot shows `judges=2, verdicts=6` (2 judges times 3 projects), and at `t+75s` the leaderboard is fully populated with per-project totals.

## How to verify

```
.venv/bin/python -m pytest packages/agents/ -q
```

Expected: 84 passed.

End-to-end smoke (requires AXL built):

```
HACKSIM_AUTO_START=true HACKSIM_AXL_BIN=$(pwd)/third_party/axl/node \
HACKSIM_PACE=smoke \
.venv/bin/uvicorn packages.orchestrator.api:app --port 8000 &
sleep 3
ID=$(curl -s -X POST http://127.0.0.1:8000/api/sim \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"a research hackathon","config":{"pace":"smoke","builders":3,"judges":2,"designers":2}}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')
sleep 75
curl -s http://127.0.0.1:8000/api/sim/$ID/snapshot \
  | python3 -c 'import sys,json; s=json.load(sys.stdin); print(f"phase={s[\"phase\"]} bounties={len(s[\"bounties\"])} projects={len(s[\"projects\"])} verdicts={len(s[\"verdicts\"])}")'
```

Expected: `phase=4 bounties=2 projects=3 verdicts=6`.

## Gensyn surface used

No new endpoints. The change is purely about which payload the worker writes to its own log file.

## Up next

Commit 30 lands the `make demo` target so the orchestrator and the frontend boot together. Then we wire the frontend's `NEXT_PUBLIC_USE_MOCKS=false` path so the real demo loads the live sim end to end.
