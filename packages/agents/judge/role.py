"""Judge run loop.

- BOUNTY_DESIGN: accumulate `bounty.posted` envelopes (we need them to
  resolve each project's bounty during JUDGING).
- BUILD: accumulate `project.submitted` envelopes.
- JUDGING: score every accumulated project against our rubric and
  broadcast one `verdict.published` envelope per project.
"""

from __future__ import annotations

from packages.agents._runtime import WorkerState, loop_until_closed
from packages.protocol import Envelope, Phase, encode_envelope, make_envelope
from packages.skills.hacksim_network.hacksim_network import SkillContext

from .decisions import score_project
from .persona import (
    CRITERIA,
    archetype_for_peer_id,
    display_name_for_peer_id,
)


def run(ctx: SkillContext) -> None:
    state = WorkerState(ctx=ctx, client=ctx.client())
    state.bounties = {}  # type: ignore[attr-defined]
    state.projects = {}  # type: ignore[attr-defined]
    state.scored = set()  # type: ignore[attr-defined]
    state.rubric_published = False  # type: ignore[attr-defined]

    state.register("bounty.posted", _on_bounty_posted)
    state.register("project.submitted", _on_project_submitted)
    state.register("phase.tick", _on_phase_tick)
    loop_until_closed(state)


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
        sent = 0
        for peer_id in state.client.all_peer_ids():
            try:
                state.client.send(peer_id, wire)
                sent += 1
            except Exception:
                pass
        state.rubric_published = True  # type: ignore[attr-defined]
        state.emit("rubric.published", {"archetype": archetype["name"], "sent_to": sent})

    projects = list(state.projects.values())  # type: ignore[attr-defined]
    if not projects:
        state.emit("judge.no_projects", {})
        return

    for project in projects:
        pid = str(project.get("project_id") or project.get("id") or "")
        if not pid or pid in state.scored:  # type: ignore[attr-defined]
            continue
        bounty = state.bounties.get(str(project.get("bounty_id") or ""))  # type: ignore[attr-defined]
        verdict = score_project(
            project=project,
            bounty=bounty,
            judge_peer_id=topo.our_public_key,
        )
        verdict.setdefault("id", f"verdict_{pid}_{topo.our_public_key[:8]}")

        env_out = make_envelope(
            type="verdict.published",
            round=Phase.JUDGING,
            sender_id=topo.our_public_key,
            payload=verdict,
        )
        wire = encode_envelope(env_out)
        sent = 0
        for peer_id in state.client.all_peer_ids():
            try:
                state.client.send(peer_id, wire)
                sent += 1
            except Exception:
                pass

        state.scored.add(pid)  # type: ignore[attr-defined]
        state.emit(
            "verdict.published",
            {
                "project_id": pid,
                "total": verdict["total"],
                "scores": verdict["scores"],
                "archetype": verdict.get("archetype"),
                "sent_to": sent,
            },
        )
