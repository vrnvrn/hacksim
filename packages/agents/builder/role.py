"""Builder run loop.

- Listen for `bounty.posted`, accumulate.
- On `phase.tick` to TEAM_FORMATION, pick the best bounty for our
  skills and broadcast `team.formed` (solo team for now; multi-builder
  team formation is a stretch).
- On `phase.tick` to BUILD, write the project artefact, git commit,
  broadcast `project.submitted`.
"""

from __future__ import annotations

import json
import os
import secrets
import time
import urllib.error
import urllib.request
from pathlib import Path

from packages.agents._runtime import WorkerState, loop_until_closed
from packages.protocol import Envelope, Phase, encode_envelope, make_envelope
from packages.skills.hacksim_network.hacksim_network import SkillContext

from .build import write_project
from .decisions import pick_bounty
from .persona import display_name_for_peer_id, skill_profile_for_peer_id


def _post_artefact_to_orchestrator(state: WorkerState, payload: dict) -> None:
    """Tell the orchestrator about our submission so it can git-archive
    the working tree under sim-runs/{sim_id}/projects/{project_id}/.

    Filesystem registration, not agent control.

    The agent control plane in HackSim rides AXL: phase ticks, bounty
    announcements, team formations, project submissions, rubrics, and
    verdicts all flow through `POST /send` envelopes that drain from
    `/recv`. This call is the second HTTP channel: builders also POST
    artefact metadata directly to the orchestrator (over a separate
    HTTP connection, not the AXL bridge) so the orchestrator can run
    `git archive` on the builder's working tree and serve the result
    under a strict CSP for the showcase iframe.

    Removing this call breaks the showcase modal Demo and Code tabs
    but does not silence the simulation; envelopes keep flowing. The
    qualification gate is satisfied by the AXL channel alone.

    No-op when HACKSIM_ORCH_URL is not set (smoke harness mode).
    """
    orch = os.environ.get("HACKSIM_ORCH_URL")
    if not orch:
        return
    url = f"{orch.rstrip('/')}/api/sim/{state.ctx.sim_id}/projects"
    body = json.dumps(payload).encode("utf-8")

    # One initial attempt plus one retry. The 15-node spawn can briefly
    # saturate the orchestrator on slow loopbacks; a single retry with a
    # short backoff covers transient failures without inflating the
    # average submit time. After two failures we emit
    # builder.artefact_register_failed so the run log shows it instead
    # of the user finding an empty showcase modal at the end.
    last_error: dict | None = None
    for attempt in range(2):
        if attempt:
            time.sleep(0.5)
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                state.emit(
                    "orch.registered",
                    {
                        "status": resp.status,
                        "project_id": payload.get("project_id"),
                        "attempts": attempt + 1,
                    },
                )
                return
        except urllib.error.HTTPError as e:
            last_error = {
                "status": e.code,
                "body": e.read(200).decode("utf-8", "replace"),
                "attempt": attempt + 1,
            }
        except Exception as e:
            last_error = {"error": str(e), "attempt": attempt + 1}
    if last_error is not None:
        state.emit("orch.register_error", last_error)
        state.emit(
            "builder.artefact_register_failed",
            {
                "project_id": payload.get("project_id"),
                "attempts": 2,
                "last_error": last_error,
            },
        )


def run(ctx: SkillContext) -> None:
    state = WorkerState(ctx=ctx, client=ctx.client())
    state.bounties = {}  # type: ignore[attr-defined]
    state.team_formed = False  # type: ignore[attr-defined]
    state.chosen_bounty = None  # type: ignore[attr-defined]
    state.team_id = None  # type: ignore[attr-defined]
    state.submitted = False  # type: ignore[attr-defined]
    state.sim_prompt = ""  # type: ignore[attr-defined]

    # Gossip the bounties we receive so other builders whose topology has not
    # expanded to include the original designer still hear about them.
    state.register("bounty.posted", _on_bounty_posted, gossip=True)
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

    chosen = pick_bounty(bounties=bounties, skills=skills, emit=state.emit)
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
    sent = state.fanout(wire, repeats=2, interval=2.0)

    state.team_formed = True  # type: ignore[attr-defined]
    # Full envelope payload to the orchestrator's snapshot, plus a second
    # diagnostic event with the broadcast counts.
    state.emit(
        "team.formed",
        {
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
    state.emit(
        "team.broadcast",
        {
            "team_id": team_id,
            "bounty_id": chosen.get("id"),
            "bounty_title": chosen.get("title"),
            "sponsor": chosen.get("sponsor_name"),
            "sent_to_initial": sent,
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

    work_dir = Path(
        os.environ.get("HACKSIM_BUILDER_WORK_DIR")
        or os.environ.get("HACKSIM_WORK_DIR")
        or os.getcwd()
    ) / "project"
    state.emit("builder.building", {"work_dir": str(work_dir)})

    try:
        result = write_project(
            work_dir=work_dir,
            bounty=state.chosen_bounty,  # type: ignore[attr-defined]
            skills=skills,
            sender_peer_id=topo.our_public_key,
            sim_prompt=state.sim_prompt,  # type: ignore[attr-defined]
            emit=state.emit,
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
    sent = state.fanout(wire, repeats=4, interval=2.0)

    state.submitted = True  # type: ignore[attr-defined]
    # Full payload to the orchestrator's snapshot, plus a diagnostic event.
    state.emit("project.submitted", dict(payload))
    state.emit(
        "project.broadcast",
        {
            "project_id": project_id,
            "files": len(result["files"]),
            "sent_to_initial": sent,
        },
    )
    _post_artefact_to_orchestrator(state, payload)
