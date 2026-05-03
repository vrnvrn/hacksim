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

import json
import os
import sys
import time

from packages.skills.hacksim_network.hacksim_network import SkillContext

from ._runtime import stub_heartbeat


KNOWN_ROLES = frozenset({"bounty_designer", "builder", "judge", "organiser"})


def _emit_misconfig(ctx: SkillContext, event_type: str, payload: dict) -> None:
    """Emit one JSON line on stdout in the same shape WorkerState.emit
    uses. Available before a WorkerState is constructed so the orchestrator
    can surface a misconfigured spawn before the stub heartbeat starts.
    """
    line = json.dumps(
        {
            "ts": time.time(),
            "role": ctx.role,
            "sim_id": ctx.sim_id,
            "type": event_type,
            "payload": payload,
        },
        separators=(",", ":"),
    )
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def main() -> int:
    try:
        ctx = SkillContext.from_env()
    except RuntimeError as e:
        sys.stderr.write(f"worker: missing environment: {e}\n")
        return 2

    role = ctx.role
    role_run = None
    import_error: str | None = None

    if role in KNOWN_ROLES:
        # Lazy import so an ImportError in one role module does not stop
        # the others from running.
        try:
            if role == "bounty_designer":
                from .bounty_designer import run as role_run  # noqa: F401, F811
            elif role == "builder":
                from .builder import run as role_run  # noqa: F401, F811
            elif role == "judge":
                from .judge import run as role_run  # noqa: F401, F811
            elif role == "organiser":
                from .organiser import run as role_run  # noqa: F401, F811
        except ImportError as exc:
            role_run = None
            import_error = str(exc)
    else:
        # Unknown role label. Surface as a structured event before the
        # stub heartbeat takes over so the orchestrator can mark the
        # spawn as misconfigured in the run log instead of silently
        # treating it as a healthy worker.
        _emit_misconfig(
            ctx,
            "worker.unknown_role",
            {"role": role, "known_roles": sorted(KNOWN_ROLES)},
        )

    if role_run is None:
        if import_error is not None:
            _emit_misconfig(
                ctx,
                "worker.import_error",
                {"role": role, "error": import_error},
            )
        # The stub heartbeat keeps the worker alive long enough for the
        # orchestrator to notice the structured event above and surface
        # the misconfiguration to the user.
        stub_heartbeat(ctx)
        return 0

    sim_prompt = os.environ.get("HACKSIM_SIM_PROMPT", "")
    try:
        role_run(ctx, sim_prompt=sim_prompt)
    except TypeError:
        # Backwards compatibility: a role.run that does not yet accept
        # sim_prompt as a keyword argument falls back to the original
        # signature. Prefer adding the parameter to the role module.
        role_run(ctx)
    return 0


if __name__ == "__main__":
    sys.exit(main())
