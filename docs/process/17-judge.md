# 17. Judge role with rubric and per-project verdicts

## What changed

Five-file role module at `packages/agents/judge/`. CLAUDE.md persona, persona.py with four archetype derivation (encouraging, balanced, strict, contrarian) keyed by sha256 of peer id, decisions.py with `score_project` and an Anthropic SDK upgrade path, role.py with the run loop accumulating bounties + projects and scoring on phase tick to JUDGING.

The five-criterion rubric (novelty, technical_depth, demo_quality, documentation, bounty_fit) is fixed across the hackathon so totals are comparable. Archetype determines the weights (sum to 1) and biases the per-criterion stub scores by ±1 or ±2 so each archetype's verdicts feel distinct.

Stub scoring is deterministic per (judge_peer_id, project_id) pair: same judge re-scoring the same project always returns the same numbers; two judges scoring the same project diverge by archetype + key hash. Lite mode runs fully without an API key.

On `phase.tick` to JUDGING, the judge first broadcasts one `rubric.published` envelope so the orchestrator and frontend learn the rubric, then iterates accumulated projects and broadcasts one `verdict.published` per project with scores, weighted total, written feedback, and the archetype tag.

19 tests cover archetype determinism and weight invariants, full verdict shape, total in range, weighted-sum equality, per-judge per-project determinism, divergence across judges and projects, no-bounty fallback, feedback mentions project or bounty, judge run-loop bounty + project accumulation, dedupe, no-op outside JUDGING, rubric and verdict broadcasts, no-projects safe path.

## How to verify

```
.venv/bin/python -m pytest packages/agents/judge/tests/ -v
```

Expected: 19 tests pass in ~4s.

## Gensyn surface used

`AxlClient.send` for the rubric and verdict broadcasts. Same fan-out pattern as the other roles. No new endpoints exercised here.

## Up next

Commit 18 lands the Organiser as the choreographer (publishes phase ticks at the right cadence + final hackathon.closed with leaderboard) plus a re-broadcast pattern in role workers so slow Yggdrasil tree propagation does not strand peers.
