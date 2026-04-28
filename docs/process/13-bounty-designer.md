# 13. BountyDesigner role

## What changed

- New module `packages/agents/bounty_designer/` with five files: `__init__.py` (exports `run`), `CLAUDE.md` (the persona prompt, also the system prompt in lite mode), `persona.py` (sponsor archetype derivation), `decisions.py` (bounty composition with Anthropic SDK and a deterministic stub fallback), `role.py` (the run loop and phase-tick handler).
- 18 tests across two files: `test_decisions.py` (sponsor pick determinism, stub shape, stub variation, JSON parsing, error paths) and `test_role.py` (handler dispatches on BOUNTY_DESIGN, ignores other phases, posts once per phase, sim_prompt update).
- The worker dispatcher in `packages/agents/worker.py` (commit 12) already routes `HACKSIM_ROLE=bounty_designer` to this module's `run`.

## Why

This is the first role to land. It exercises the full pattern that every subsequent role follows: persona file as artefact, decision module that calls Anthropic with a stub fallback, run loop that registers handlers and broadcasts envelopes via `AxlClient`. Once the next four roles ship, the demo is end to end.

The stub fallback is deliberate. `make demo` runs without an Anthropic API key set, producing real, distinct, on-theme bounties keyed off each designer's peer id and the human's prompt. With an API key set, the same designers get richer, more varied output via Claude. The fallback is a feature, not a placeholder; it is the thing that lets a reviewer hit `make demo` immediately, and a hackathon judge see something interesting without needing an Anthropic key.

Sponsor archetypes are picked deterministically from the designer's peer id (sha256 mod 8). For a sim with three to five designers, the probability of two designers picking the same sponsor is low. If it happens, both still produce distinct bounties because the stub also factors in the prompt hash.

The persona file is real CLAUDE.md content, not a placeholder. Reviewers can read it as documentation of the role's brief.

## How to verify

```
.venv/bin/python -m pytest packages/agents/bounty_designer/tests/ -v
```

Expected: 18 tests pass in roughly 2 seconds. No Anthropic API key needed for tests; the fixture clears the env var so the stub runs.

End-to-end smoke (manual, requires built AXL binary):

```python
from pathlib import Path
from packages.orchestrator import Spawner
import time

with Spawner(base_dir=Path("/tmp/hacksim_smoke"), axl_bin=Path("third_party/axl/node"), sim_id="smoke") as s:
    org = s.spawn_role(role="organiser", is_bootstrap=True)
    d0 = s.spawn_role(role="bounty_designer", index=0)
    d1 = s.spawn_role(role="bounty_designer", index=1)
    time.sleep(2)  # let everyone peer
    # Manually publish a phase.tick from the orchestrator process: TODO commit 18.
    # Or post one via curl from another shell:
    #   curl -X POST http://127.0.0.1:9202/send \
    #     -H "X-Destination-Peer-Id: <designer_peer>" \
    #     -d '{"proto":1,"type":"phase.tick","round":0,"sender_id":"00..","timestamp":0,"payload":{"phase":0}}'
```

The designer log should show `designer.composing` then `bounty.posted` events.

## Gensyn surface used

`AxlClient.get_topology` and `AxlClient.send` (via the worker's broadcast loop). Same pattern as the autoresearch demo's `broadcast_finding` (research_network.py:285-298), retyped to our `bounty.posted` envelope.

## Up next

Commit 14 lands the Builder role. It listens for `bounty.posted` envelopes, picks a bounty that matches its skill profile, and broadcasts a `team.forming` invitation.
