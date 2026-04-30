"""Judge role.

A judge writes its own rubric (criteria + weights), accumulates project
submissions, and on phase tick to JUDGING scores every project against
its rubric. Verdicts are broadcast as `verdict.published` envelopes
with written feedback.

Default scoring is deterministic per (judge_id, project_id) pair: two
judges scoring the same project return different scores, but the same
judge re-scoring the same project returns the same number. With
`ANTHROPIC_API_KEY` set, scoring upgrades to a Claude call against the
rubric and the bounty's qualification list.
"""

from .role import run

__all__ = ["run"]
