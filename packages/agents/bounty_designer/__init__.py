"""BountyDesigner role.

A bounty designer is a "sponsor" with a name, a budget, and an opinion.
On phase tick to BOUNTY_DESIGN, the designer composes one bounty and
broadcasts it as `bounty.posted` over AXL.

Lite mode (default): the run loop calls Anthropic SDK with the persona
prompt and the sim prompt, parses one bounty out of the response.
If ANTHROPIC_API_KEY is not set, the deterministic stub generator runs
instead, varying output by the designer's own peer id so each sponsor
on the mesh produces a distinct bounty.
"""

from .role import run

__all__ = ["run"]
