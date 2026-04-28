"""Python module backing the hacksim-network Claude Code skill.

The slash commands defined in `packages/skills/hacksim-network/SKILL.md`
shell out to this module. Each command is a function that reads its
inputs from JSON on stdin or argv, calls AxlClient and the protocol
module, and writes JSON to stdout.

Mirrors `skills/autoresearch-network/research_network.py` in shape:
stdlib only on the wire layer, role-specific helpers on top.
"""

from .hacksim_network import (
    SkillContext,
    cmd_status,
    cmd_recv,
    cmd_post_bounty,
    cmd_submit_project,
    main,
)

__all__ = [
    "SkillContext",
    "cmd_status",
    "cmd_recv",
    "cmd_post_bounty",
    "cmd_submit_project",
    "main",
]
