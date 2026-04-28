"""Builder run loop.

- Listen for `bounty.posted`, accumulate.
- On `phase.tick` to TEAM_FORMATION, pick the best bounty for our
  skills and broadcast `team.formed` (solo team for now; multi-builder
  team formation is a stretch).
- On `phase.tick` to BUILD, write the project artefact, git commit,
  broadcast `project.submitted`.
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path

from packages.agents._runtime import WorkerState, loop_until_closed
from packages.protocol import Envelope, Phase, encode_envelope, make_envelope
from packages.skills.hacksim_network.hacksim_network import SkillContext

from .build import write_project
from .decisions import pick_bounty
from .persona import display_name_for_peer_id, skill_profile_for_peer_id


def run(ctx: SkillContext) -> None:
    state = WorkerState(ctx=ctx, client=ctx.client())
    state.bounties = {}  # type: ignore[attr-defined]
    state.team_formed = False  # type: ignore[attr-defined]
    state.chosen_bounty = None  # type: ignore[attr-defined]
    state.team_id = None  # type: ignore[attr-defined]
    state.submitted = False  # type: ignore[attr-defined]
    state.sim_prompt = ""  # type: ignore[attr-defined]

    state.register("bounty.posted", _on_bounty_posted)
    state.register("phase.tick", _on_phase_tick)
    state.register("sim.prompt", _on_sim_prompt)
    loop_until_closed(state)


def _on_sim_prompt(state: WorkerState, env: Envelope) -> None:
    state.sim_prompt = env["payload"].get("prompt", "")  # type: ignore[attr-defined]


def _on_bounty_posted(state: WorkerState, env: Envelope) -> None:
    """Accumulate bounties seen during BOUNTY_DESIGN phase."""
    payload = env["payload"]
    bid = str(payload.get("id") or "")
    if not bid:
        return
    if bid not in state.bounties:  # type: ignore[attr-defined]
        state.bounties[bid] = payload  # type: ignore[attr-defined]
        state.emit(
            "builder.heard_bounty",
            {
                "bounty_id": bid,
                "sponsor_name": payload.get("sponsor_name"),
                "title": payload.get("title"),
            },
        )


def _on_phase_tick(state: WorkerState, env: Envelope) -> None:
    phase = env["payload"].get("phase")
    if phase == Phase.TEAM_FORMATION:
        _form_team(state)
    elif phase == Phase.BUILD:
        _build_and_submit(state)


def _form_team(state: WorkerState) -> None:
    if state.team_formed:  # type: ignore[attr-defined]
        return

    topo = state.client.get_topology()
    skills = skill_profile_for_peer_id(topo.our_public_key)

    bounties = list(state.bounties.values())  # type: ignore[attr-defined]
    if not bounties:
        state.emit("builder.no_bounty", {"reason": "no bounty.posted envelopes received"})
        return

    chosen = pick_bounty(bounties=bounties, skills=skills)
    if chosen is None:
        state.emit("builder.no_bounty", {"reason": "pick returned None"})
        return

    team_id = f"team_{secrets.token_hex(3)}"
    state.chosen_bounty = chosen  # type: ignore[attr-defined]
    state.team_id = team_id  # type: ignore[attr-defined]

    formed = make_envelope(
        type="team.formed",
        round=Phase.TEAM_FORMATION,
        sender_id=topo.our_public_key,
        payload={
            "id": team_id,
            "team_id": team_id,
            "bounty_id": chosen.get("id"),
            "members": [topo.our_public_key],
            "display_names": [display_name_for_peer_id(topo.our_public_key)],
            "skills_summary": {
                display_name_for_peer_id(topo.our_public_key): skills,
            },
        },
    )
    wire = encode_envelope(formed)
    sent = 0
    for peer_id in state.client.all_peer_ids():
        try:
            state.client.send(peer_id, wire)
            sent += 1
        except Exception:
            pass

    state.team_formed = True  # type: ignore[attr-defined]
    state.emit(
        "team.formed",
        {
            "team_id": team_id,
            "bounty_id": chosen.get("id"),
            "bounty_title": chosen.get("title"),
            "sponsor": chosen.get("sponsor_name"),
            "members": 1,
            "sent_to": sent,
        },
    )


def _build_and_submit(state: WorkerState) -> None:
    if state.submitted:  # type: ignore[attr-defined]
        return
    if not state.chosen_bounty:  # type: ignore[attr-defined]
        state.emit("builder.no_team", {"reason": "no chosen bounty when BUILD started"})
        return

    topo = state.client.get_topology()
    skills = skill_profile_for_peer_id(topo.our_public_key)

    work_dir = Path(os.environ.get("HACKSIM_BUILDER_WORK_DIR", os.getcwd())) / "project"
    state.emit("builder.building", {"work_dir": str(work_dir)})

    try:
        result = write_project(
            work_dir=work_dir,
            bounty=state.chosen_bounty,  # type: ignore[attr-defined]
            skills=skills,
            sender_peer_id=topo.our_public_key,
            sim_prompt=state.sim_prompt,  # type: ignore[attr-defined]
        )
    except Exception as e:
        state.emit("builder.build_error", {"error": str(e)})
        return

    project_id = f"proj_{secrets.token_hex(4)}"
    payload = {
        "id": project_id,
        "project_id": project_id,
        "team_id": state.team_id,  # type: ignore[attr-defined]
        "bounty_id": state.chosen_bounty.get("id"),  # type: ignore[attr-defined]
        "title": result["title"],
        "tagline": result["tagline"],
        "commit_hash": result["commit_hash"],
        "entry_path": result["entry_path"],
        "working_dir": str(work_dir),
        "files": result["files"],
    }

    submitted = make_envelope(
        type="project.submitted",
        round=Phase.BUILD,
        sender_id=topo.our_public_key,
        payload=payload,
    )
    wire = encode_envelope(submitted)
    sent = 0
    for peer_id in state.client.all_peer_ids():
        try:
            state.client.send(peer_id, wire)
            sent += 1
        except Exception:
            pass

    state.submitted = True  # type: ignore[attr-defined]
    state.emit(
        "project.submitted",
        {
            "project_id": project_id,
            "title": result["title"],
            "commit_hash": result["commit_hash"],
            "files": len(result["files"]),
            "sent_to": sent,
        },
    )
