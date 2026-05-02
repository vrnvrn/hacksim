"""Organiser run loop.

On worker.started we schedule four `phase.tick` broadcasts (BOUNTY_DESIGN,
TEAM_FORMATION, BUILD, JUDGING) at the configured pace. We also schedule
the `hackathon.closed` tally to fire at the end of JUDGING.

Throughout the simulation we accumulate `project.submitted` and
`verdict.published` envelopes so we can compose the leaderboard.

The organiser is always the bootstrap node, so it has the cleanest
view of the mesh and is the natural choreographer. It does not score,
sponsor, or build.
"""

from __future__ import annotations

import os
import time
import uuid

from packages.agents._runtime import WorkerState, loop_until_closed
from packages.protocol import Envelope, Phase, encode_envelope, make_envelope
from packages.skills.hacksim_network.hacksim_network import SkillContext

from .persona import DEFAULT_CLOSE_AT, PACE_PRESETS
from .tally import tally_leaderboard


def run(ctx: SkillContext) -> None:
    state = WorkerState(ctx=ctx, client=ctx.client())
    state.projects = {}  # type: ignore[attr-defined]
    state.verdicts = {}  # type: ignore[attr-defined]
    state.closed_emitted = False  # type: ignore[attr-defined]
    state.judges = {}  # type: ignore[attr-defined]
    state.bounties = {}  # type: ignore[attr-defined]
    state.mcp_called = set()  # type: ignore[attr-defined]

    # The organiser is the bootstrap, so every other role connects to it
    # directly. That makes it the natural relay: registering gossip=True for
    # every envelope type that needs broad propagation closes the gap when
    # role-to-role topology is sparse.
    state.register("bounty.posted", _on_bounty_posted, gossip=True)
    state.register("team.formed", _on_relay_only, gossip=True)
    state.register("rubric.published", _on_rubric_published, gossip=True)
    state.register("project.submitted", _on_project_submitted, gossip=True)
    state.register("verdict.published", _on_verdict_published, gossip=True)

    pace_name = os.environ.get("HACKSIM_PACE", "quick")
    pace = PACE_PRESETS.get(pace_name, PACE_PRESETS["quick"])

    state.schedule(_make_phase_emitter(Phase.BOUNTY_DESIGN), pace["bounty_design_at"])
    state.schedule(_make_phase_emitter(Phase.TEAM_FORMATION), pace["team_formation_at"])
    state.schedule(_make_phase_emitter(Phase.BUILD), pace["build_at"])
    state.schedule(_make_phase_emitter(Phase.JUDGING), pace["judging_at"])
    state.schedule(_close_hackathon, pace.get("close_at", DEFAULT_CLOSE_AT))

    state.emit("organiser.scheduled", {"pace": pace_name, "close_at": pace.get("close_at")})
    loop_until_closed(state)


def _make_phase_emitter(phase: int):
    def _emit(state: WorkerState) -> None:
        topo = state.client.get_topology()
        env = make_envelope(
            type="phase.tick",
            round=phase,
            sender_id=topo.our_public_key,
            payload={"phase": phase, "id": f"phase_{phase}"},
        )
        wire = encode_envelope(env)
        sent = state.fanout(wire, repeats=2, interval=1.5)
        # Emit the phase.tick payload itself so the orchestrator's
        # snapshot accumulator sees it. Diagnostic counts go on a
        # separate `phase.tick.broadcast` event.
        state.emit("phase.tick", {"phase": phase, "id": f"phase_{phase}"})
        state.emit(
            "phase.tick.broadcast",
            {"phase": phase, "sent_to_initial": sent},
        )

    return _emit


def _on_relay_only(state: WorkerState, env: Envelope) -> None:
    """No-op handler used by the runtime so gossip fires for envelope
    types the organiser does not act on but still relays."""
    return None


def _on_bounty_posted(state: WorkerState, env: Envelope) -> None:
    """Track bounties so the MCP score call carries the right qualification list."""
    bid = str(env["payload"].get("id") or "")
    if bid and bid not in state.bounties:  # type: ignore[attr-defined]
        state.bounties[bid] = env["payload"]  # type: ignore[attr-defined]


def _on_rubric_published(state: WorkerState, env: Envelope) -> None:
    """Track judge identities so the organiser can call them via MCP later."""
    payload = env["payload"]
    judge = str(payload.get("judge_peer_id") or env["sender_id"])
    if judge and judge not in state.judges:  # type: ignore[attr-defined]
        state.judges[judge] = payload  # type: ignore[attr-defined]


def _on_project_submitted(state: WorkerState, env: Envelope) -> None:
    pid = str(env["payload"].get("project_id") or env["payload"].get("id") or "")
    if pid and pid not in state.projects:  # type: ignore[attr-defined]
        state.projects[pid] = env["payload"]  # type: ignore[attr-defined]


def _on_verdict_published(state: WorkerState, env: Envelope) -> None:
    pid = str(env["payload"].get("project_id") or "")
    judge = str(env["payload"].get("judge_peer_id") or env["sender_id"])
    if not pid:
        return
    by_proj = state.verdicts.setdefault(pid, {})  # type: ignore[attr-defined]
    if judge in by_proj:
        return  # dedupe by judge per project
    by_proj[judge] = env["payload"]
    # Schedule one MCP confirmation per (judge, project) shortly after
    # the envelope verdict lands. The MCP call exercises the typed
    # JSON-RPC surface and emits mcp.score_received so the run log shows
    # the round trip happening live. We tolerate state objects built
    # outside `run()` (some tests do) by lazily initialising the dedupe
    # set and the project/bounty lookups.
    mcp_called = getattr(state, "mcp_called", None)
    if mcp_called is None:
        mcp_called = set()
        state.mcp_called = mcp_called  # type: ignore[attr-defined]
    key = (judge, pid)
    if key in mcp_called:
        return
    mcp_called.add(key)
    projects = getattr(state, "projects", {}) or {}
    project = projects.get(pid)
    if not project:
        return
    bounties = getattr(state, "bounties", {}) or {}
    bounty = bounties.get(str(project.get("bounty_id") or ""))
    state.schedule(
        lambda s, j=judge, p=project, b=bounty: _confirm_via_mcp(s, j, p, b),
        delay=0.5,
    )


def _confirm_via_mcp(
    state: WorkerState,
    judge_peer_id: str,
    project: dict,
    bounty: dict | None,
) -> None:
    """Round-trip the verdict through `/mcp/{judge}/judge` for proof of
    typed JSON-RPC across the mesh.

    The result here matches the envelope-based verdict the judge already
    broadcast; the MCP path is supplemental, not the source of truth. We
    surface the round trip on the SSE stream as `mcp.score_requested`
    and `mcp.score_received` so a viewer can watch the typed surface
    fire without reading the JSON-RPC body.
    """
    pid = str(project.get("project_id") or project.get("id") or "")
    rpc_id = uuid.uuid4().hex[:12]
    rpc_body = {
        "jsonrpc": "2.0",
        "id": rpc_id,
        "method": "tools/call",
        "params": {
            "name": "score_project",
            "arguments": {"project": project, "bounty": bounty or {}},
        },
    }
    started = time.monotonic()
    state.emit(
        "mcp.score_requested",
        {
            "judge_peer_id": judge_peer_id,
            "project_id": pid,
            "rpc_id": rpc_id,
        },
    )
    try:
        reply = state.client.mcp_call(judge_peer_id, "judge", rpc_body, timeout=15.0)
    except Exception as e:
        state.emit(
            "mcp.score_failed",
            {
                "judge_peer_id": judge_peer_id,
                "project_id": pid,
                "rpc_id": rpc_id,
                "error_class": type(e).__name__,
                "error": str(e)[:200],
            },
        )
        return

    elapsed_ms = int((time.monotonic() - started) * 1000)
    inner = reply.get("response") or {}
    err = inner.get("error")
    if err:
        state.emit(
            "mcp.score_failed",
            {
                "judge_peer_id": judge_peer_id,
                "project_id": pid,
                "rpc_id": rpc_id,
                "error": str(err.get("message") or err)[:200],
            },
        )
        return
    result = inner.get("result") or {}
    structured = (
        result.get("structuredContent")
        if isinstance(result, dict)
        else None
    )
    total = (structured or {}).get("total")
    state.emit(
        "mcp.score_received",
        {
            "judge_peer_id": judge_peer_id,
            "project_id": pid,
            "rpc_id": rpc_id,
            "elapsed_ms": elapsed_ms,
            "total": total,
        },
    )


def _close_hackathon(state: WorkerState) -> None:
    if state.closed_emitted:  # type: ignore[attr-defined]
        return

    # Flatten verdicts dict-of-dicts into list-of-lists.
    verdicts_by_project = {
        pid: list(judges.values())
        for pid, judges in state.verdicts.items()  # type: ignore[attr-defined]
    }
    leaderboard = tally_leaderboard(
        projects=state.projects,  # type: ignore[attr-defined]
        verdicts_by_project=verdicts_by_project,
    )

    topo = state.client.get_topology()
    env = make_envelope(
        type="hackathon.closed",
        round=Phase.SHOWCASE,
        sender_id=topo.our_public_key,
        payload={
            "id": "hackathon_closed",
            "leaderboard": leaderboard,
            "project_count": len(leaderboard),
            "verdict_count": sum(r["verdicts"] for r in leaderboard),
        },
    )
    wire = encode_envelope(env)
    sent = state.fanout(wire, repeats=2, interval=1.5)

    state.closed_emitted = True  # type: ignore[attr-defined]
    # Emit the full hackathon.closed payload so the orchestrator's
    # snapshot accumulator sees the leaderboard in full. Diagnostic info
    # lands on the separate `hackathon.closed.broadcast` event.
    state.emit(
        "hackathon.closed",
        {
            "id": "hackathon_closed",
            "leaderboard": leaderboard,
            "project_count": len(leaderboard),
            "verdict_count": sum(r["verdicts"] for r in leaderboard),
        },
    )
    state.emit(
        "hackathon.closed.broadcast",
        {"sent_to_initial": sent, "winners_top3": leaderboard[:3]},
    )

    # After a brief grace period for the showcase, ask the worker to stop.
    state.schedule(lambda s: setattr(s, "closed", True), 5.0)
