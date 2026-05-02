# 63. README "every agent" tightened to "every decision-making role"

## What changed

The Prerequisites bullet for `ANTHROPIC_API_KEY` read:

> Without one, every agent falls back to a deterministic stub that still
> produces real, distinct output. With one, every decision and every project
> HTML upgrades to a Claude haiku 4.5 call.

A strict reader could parse "every agent" two ways: (a) every running agent
process has Anthropic-driven decisions (false; the organiser is choreography
only and never calls the SDK), or (b) the deterministic-stub fallback applies
across the whole role population (true). The reality audit
(`refs/REALITY_AUDIT_2026-05-02.md` D6) flagged the ambiguity.

Tightened to:

> Without one, every decision-making role (designer, builder, judge) falls
> back to a deterministic stub keyed off peer id and prompt hash, producing
> real, distinct output. With one, every bounty, every project HTML, and
> every verdict upgrades to a Claude haiku 4.5 call (the organiser is
> choreography only and never calls the SDK).

Same scope, tighter mapping. The FAQ on the home page already had the
precise four-call-sites-across-three-roles framing; the README now matches.

## Why this needed its own commit

Surface-area accuracy. The README is the front door for reviewers; an
ambiguity that reads as "all four roles call Claude" misrepresents the
system the moment a reader checks `packages/agents/organiser/role.py` and
finds zero SDK imports.

## Verify

`bash scripts/hooks/pre-commit.sh` exits 0 against the staged diff.

## Files

`README.md`.
