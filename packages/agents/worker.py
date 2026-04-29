"""HackSim role worker entrypoint.

Reads HACKSIM_ROLE from the environment and dispatches to the matching
role module's run() function. Roles that have not landed yet fall back
to the stub heartbeat loop so the harness can be smoke-tested before
agent personas are written.

Invoked by the orchestrator's Spawner via:

    python -m packages.agents.worker
"""

from __future__ import annotations

import sys

from packages.skills.hacksim_network.hacksim_network import SkillContext

from ._runtime import stub_heartbeat


def main() -> int:
    try:
        ctx = SkillContext.from_env()
    except RuntimeError as e:
        sys.stderr.write(f"worker: missing environment: {e}\n")
        return 2

    # Role dispatch. Lazy import so unimplemented roles do not break
    # the harness while commits 13+ are landing.
    role = ctx.role
    role_run = None
    try:
        if role == "bounty_designer":
            from .bounty_designer import run as role_run  # noqa: F401, F811
        elif role == "builder":
            from .builder import run as role_run  # noqa: F401, F811
        elif role == "judge":
            from .judge import run as role_run  # noqa: F401, F811
        elif role == "organiser":
            from .organiser import run as role_run  # noqa: F401, F811
    except ImportError:
        role_run = None

    if role_run is None:
        # Roles not yet implemented run the stub. Useful for the spawner
        # smoke test and for any role we have not built yet.
        stub_heartbeat(ctx)
        return 0

    role_run(ctx)
    return 0


if __name__ == "__main__":
    sys.exit(main())
