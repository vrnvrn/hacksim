"""BountyDesigner role.

A bounty designer is a "sponsor" with a name, a budget, and an opinion.
On phase tick to BOUNTY_DESIGN, the designer composes one bounty and
broadcasts it as `bounty.posted` over AXL.

Two decision paths, same envelope shape:
- With `ANTHROPIC_API_KEY` set, the run loop calls Claude haiku 4.5
  against the persona prompt and the sim prompt, then parses one bounty
  out of the response.
- Without a key, a deterministic stub varies output by the designer's
  own peer id so each sponsor on the mesh produces a distinct bounty.
"""

from .role import run

__all__ = ["run"]
