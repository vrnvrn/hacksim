"""HackSim role worker entrypoint.

Reads HACKSIM_ROLE from the environment and dispatches to the matching
role module's run() function. All four shipping roles (bounty_designer,
builder, judge, organiser) live under packages.agents.<role>; the stub
heartbeat at the bottom is a safety net for unknown role labels and for
ImportError on the role module, so a misconfigured spawn cannot wedge
the worker process.

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

    # Role dispatch. Lazy import so an ImportError in one role module
    # does not stop the others from running.
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
        # Unknown role label or import failure. The stub heartbeat keeps
        # the worker alive long enough for the orchestrator to notice and
        # surface the misconfiguration in the run log.
        stub_heartbeat(ctx)
        return 0

    role_run(ctx)
    return 0


if __name__ == "__main__":
    sys.exit(main())
