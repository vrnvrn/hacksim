# 55. Drop the lite-vs-Claude-Code mode framing in source docstrings

## What changed

Several Python source docstrings still framed the worker stack as
"lite mode (default)" plus "Claude Code mode (stretch)" or treated the
spawner's lack of Claude Code spawning as a temporary commit-12 task.
Claude Code spawning is not on the path; the Python worker is the
path. The two real decision branches inside each role are the
deterministic stub and the Anthropic SDK call. Updated the prose so a
judge reading the source reads what runs.

Files changed:

- `packages/agents/__init__.py`: package docstring describes the two
  decision paths (deterministic default plus Claude when
  ANTHROPIC_API_KEY is set), each emitting the same envelope shape.
- `packages/agents/bounty_designer/__init__.py`: drops the
  "Lite mode (default)" framing; describes the two paths directly.
- `packages/agents/bounty_designer/decisions.py`: same reframing
  applied to the bounty composition module-level docstring.
- `packages/agents/bounty_designer/persona.py`: `load_persona_text`
  docstring stops referencing "Claude Code mode"; explains the
  persona is the Anthropic SDK system prompt and the file ships in
  the GitHub repo so reviewers can read every role's brief.
- `packages/agents/builder/__init__.py`: bounty pick is deterministic
  by default with Claude upgrade when the key is set; HTML generation
  follows the same pattern.
- `packages/agents/judge/__init__.py`: scoring is deterministic per
  (judge_id, project_id) by default, Claude-driven when the key is
  set.
- `packages/agents/judge/decisions.py`: same reframing for the
  scoring module.
- `packages/orchestrator/spawner.py`: file-level docstring stops
  framing the absence of Claude Code spawning as "lands in commit 12";
  describes the two process trees (AXL Go binary plus Python worker)
  the spawner actually manages.

No code paths change.

## Why

The dual-mode framing implied a near-term commitment to ship a
Claude Code spawning path. The submission shape is the Python worker;
that is what runs on every demo. Calling the deterministic path
"lite mode" frames it as the lesser of two implementations when in
fact it is the production default. A panel reading the source should
read what runs, not what we considered shipping.

## How to verify

```
.venv/bin/pytest packages/ -q
```

260 tests pass; no behaviour changes (comment-only edit).

```
rg -n 'lite mode|Claude Code mode|stretch mode' packages/
```

No matches in source code. The remaining historical references live
in `docs/process/07`, `10`, `11`, `12`, `13`, `17`, `18` (notes that
describe what was true at each commit's time) and refs/PLAN.md, all
of which are intentionally chronological.

## Gensyn surface used

None.

## Up next

Soften one user-facing copy line in `HowItWorks` that paired
"Live feed" with "real AXL mesh" in a way the hosted-preview banner
had to walk back.
