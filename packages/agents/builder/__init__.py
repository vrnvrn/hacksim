"""Builder role.

A builder has a skill profile, listens for bounties posted by designers,
picks the bounty that best fits its skills, and forms a team.

Phase lifecycle:
- BOUNTY_DESIGN: accumulate bounty.posted envelopes.
- TEAM_FORMATION: pick a bounty, broadcast team.formed.
- BUILD: write a project, broadcast project.submitted.
- JUDGING / SHOWCASE: idle.

Bounty pick uses a deterministic skill-overlap score by default; with
`ANTHROPIC_API_KEY` set, the pick upgrades to a reasoned choice via
Claude. Project HTML is generated similarly: deterministic templates
keyed off the bounty plus the builder's peer id, upgraded to a Claude
call when the key is set. Both paths produce a real, runnable
single-page web project.
"""

from .role import run

__all__ = ["run"]
