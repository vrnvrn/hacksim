"""Builder role.

A builder has a skill profile, listens for bounties posted by designers,
picks the bounty that best fits its skills, and forms a team.

Phase lifecycle:
- BOUNTY_DESIGN: accumulate bounty.posted envelopes.
- TEAM_FORMATION: pick a bounty, broadcast team.formed.
- BUILD: write a project, broadcast project.submitted (commit 15).
- JUDGING / SHOWCASE: idle.

Lite mode picks the bounty using a deterministic skill-overlap score;
Anthropic SDK upgrades the pick to a reasoned choice when the API key
is set.
"""

from .role import run

__all__ = ["run"]
