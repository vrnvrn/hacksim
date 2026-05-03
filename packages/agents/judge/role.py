"""Judge run loop.

- BOUNTY_DESIGN: accumulate `bounty.posted` envelopes (we need them to
  resolve each project's bounty during JUDGING).
- BUILD: accumulate `project.submitted` envelopes.
- JUDGING: score every accumulated project against our rubric and
  broadcast one `verdict.published` envelope per project.
"""

from __future__ import annotations

import os

from packages.agents._runtime import WorkerState, loop_until_closed
from packages.protocol import Envelope, Phase, encode_envelope, make_envelope
from packages.skills.hacksim_network.hacksim_network import SkillContext

from .decisions import score_project
from .mcp_service import McpService
from .persona import (
    CRITERIA,
    archetype_for_peer_id,
    display_name_for_peer_id,
)


_JUDGE_RETRY_DELAY_S = 5.0
_JUDGE_RETRY_BUDGET = 6  # 6 retries x 5s = 30s of slack past the JUDGING tick.


def run(ctx: SkillContext) -> None:
    state = WorkerState(ctx=ctx, client=ctx.client())
    state.bounties = {}  # type: ignore[attr-defined]
    state.projects = {}  # type: ignore[attr-defined]
    state.scored = set()  # type: ignore[attr-defined]
    state.rubric_published = False  # type: ignore[attr-defined]
    state.judge_retries_left = 0  # type: ignore[attr-defined]

    # Gossip bounty.posted and project.submitted so peers whose topology
    # was sparse at the original broadcast still hear about them.
    state.register("bounty.posted", _on_bounty_posted, gossip=True)
    state.register("project.submitted", _on_project_submitted, gossip=True)
    state.register("phase.tick", _on_phase_tick)

    # When the spawner allocated a router port for us, AXL will forward
    # inbound /mcp/{our_peer}/judge requests to 127.0.0.1:<port>/route.
    # Stand up the MCP service before entering the run loop so an early
    # caller does not race the judge's startup. The persona (peer id) is
    # not known until /topology resolves; query it here.
    mcp_port_str = os.environ.get("HACKSIM_MCP_ROUTER_PORT")
    mcp_service: McpService | None = None
    if mcp_port_str:
        try:
            our_peer = state.client.get_topology().our_public_key
        except Exception as e:
            state.emit(
                "mcp.service_start_failed",
                {"reason": "topology unreachable", "error": str(e)},
            )
            our_peer = ""
        if our_peer:
            mcp_service = McpService(
                judge_peer_id=our_peer,
                port=int(mcp_port_str),
                emit=state.emit,
            )
            mcp_service.start()

    try:
        loop_until_closed(state)
    finally:
        if mcp_service is not None:
            mcp_service.stop()


def _on_bounty_posted(state: WorkerState, env: Envelope) -> None:
    payload = env["payload"]
    bid = str(payload.get("id") or "")
    if bid and bid not in state.bounties:  # type: ignore[attr-defined]
        state.bounties[bid] = payload  # type: ignore[attr-defined]


def _on_project_submitted(state: WorkerState, env: Envelope) -> None:
    payload = env["payload"]
    pid = str(payload.get("project_id") or payload.get("id") or "")
    if pid and pid not in state.projects:  # type: ignore[attr-defined]
        state.projects[pid] = payload  # type: ignore[attr-defined]
        state.emit(
            "judge.heard_project",
            {
                "project_id": pid,
                "title": payload.get("title"),
                "bounty_id": payload.get("bounty_id"),
            },
        )


def _on_phase_tick(state: WorkerState, env: Envelope) -> None:
    if env["payload"].get("phase") != Phase.JUDGING:
        return
    # Reset the retry budget on every JUDGING tick so a sim-restart
    # picks up a fresh window.
    state.judge_retries_left = _JUDGE_RETRY_BUDGET  # type: ignore[attr-defined]
    _judge_round(state)


def _judge_round(state: WorkerState) -> None:
    """Publish the rubric (once) and score every unscored project.

    project.submitted envelopes propagate through the loopback mesh
    asynchronously. A judge that runs the JUDGING tick the moment it
    fires can find state.projects empty (or partial) because the
    builder broadcasts have not drained yet. Schedule a retry until
    the per-judge budget is exhausted; the scored set keeps the loop
    idempotent across retries.
    """
    topo = state.client.get_topology()
    archetype = archetype_for_peer_id(topo.our_public_key)

    if not state.rubric_published:  # type: ignore[attr-defined]
        rubric_env = make_envelope(
            type="rubric.published",
            round=Phase.JUDGING,
            sender_id=topo.our_public_key,
            payload={
                "id": f"rubric_{topo.our_public_key[:8]}",
                "judge_peer_id": topo.our_public_key,
                "judge_name": display_name_for_peer_id(topo.our_public_key),
                "archetype": archetype["name"],
                "rubric": [
                    {
                        "name": crit,
                        "weight": archetype["weights"][i],
                        "description": f"How {crit.replace('_', ' ')} this submission is.",
                    }
                    for i, crit in enumerate(CRITERIA)
                ],
            },
        )
        wire = encode_envelope(rubric_env)
        sent = state.fanout(wire, repeats=2, interval=2.0)
        state.rubric_published = True  # type: ignore[attr-defined]
        # Emit the full envelope payload so the orchestrator's snapshot
        # accumulator gets the judge_peer_id and rubric. Diagnostic info
        # goes on a separate event.
        state.emit("rubric.published", dict(rubric_env["payload"]))
        state.emit(
            "rubric.broadcast",
            {"archetype": archetype["name"], "sent_to_initial": sent},
        )

    projects = list(state.projects.values())  # type: ignore[attr-defined]
    unscored = [
        project
        for project in projects
        if (
            (pid := str(project.get("project_id") or project.get("id") or ""))
            and pid not in state.scored  # type: ignore[attr-defined]
        )
    ]

    retries_left = getattr(state, "judge_retries_left", 0)

    if not unscored:
        if retries_left > 0:
            state.judge_retries_left = retries_left - 1  # type: ignore[attr-defined]
            state.emit("judge.no_projects", {"retries_left": retries_left})
            state.schedule(_judge_round, _JUDGE_RETRY_DELAY_S)
            return
        # Budget exhausted; no projects ever arrived. Final emit so the
        # run log makes the bail visible.
        state.emit("judge.no_projects", {"retries_left": 0, "final": True})
        return

    for project in unscored:
        pid = str(project.get("project_id") or project.get("id") or "")
        bounty = state.bounties.get(str(project.get("bounty_id") or ""))  # type: ignore[attr-defined]
        verdict = score_project(
            project=project,
            bounty=bounty,
            judge_peer_id=topo.our_public_key,
            emit=state.emit,
        )
        verdict.setdefault("id", f"verdict_{pid}_{topo.our_public_key[:8]}")

        env_out = make_envelope(
            type="verdict.published",
            round=Phase.JUDGING,
            sender_id=topo.our_public_key,
            payload=verdict,
        )
        wire = encode_envelope(env_out)
        sent = state.fanout(wire, repeats=2, interval=2.0)

        state.scored.add(pid)  # type: ignore[attr-defined]
        state.emit("verdict.published", dict(verdict))
        state.emit(
            "verdict.broadcast",
            {"project_id": pid, "sent_to_initial": sent},
        )

    # More projects might still arrive; keep checking while we have
    # budget. The scored set makes the next round idempotent.
    if retries_left > 0:
        state.judge_retries_left = retries_left - 1  # type: ignore[attr-defined]
        state.schedule(_judge_round, _JUDGE_RETRY_DELAY_S)
