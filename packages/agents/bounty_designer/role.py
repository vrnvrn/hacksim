"""BountyDesigner run loop.

Listens for `phase.tick` to BOUNTY_DESIGN. When it arrives, the designer
composes one bounty (via decisions.propose_bounty) and broadcasts it
as a `bounty.posted` envelope. Re-broadcasts within the same phase are
suppressed so each designer posts exactly one bounty per round.
"""

from __future__ import annotations

import secrets

from packages.agents._runtime import WorkerState, loop_until_closed
from packages.protocol import Envelope, Phase, encode_envelope, make_envelope
from packages.skills.hacksim_network.hacksim_network import SkillContext

from .decisions import propose_bounty
from .persona import sponsor_for_peer_id


def run(ctx: SkillContext, *, sim_prompt: str | None = None) -> None:
    """Entrypoint dispatched from packages.agents.worker.

    `sim_prompt` is supplied by the choreography via env var
    HACKSIM_SIM_PROMPT or as the first phase.tick payload field.
    """
    state = WorkerState(ctx=ctx, client=ctx.client())
    state.posted = False  # type: ignore[attr-defined]
    state.sim_prompt = sim_prompt or ""  # type: ignore[attr-defined]
    state.register("phase.tick", _on_phase_tick)
    state.register("sim.prompt", _on_sim_prompt)
    loop_until_closed(state)


def _on_sim_prompt(state: WorkerState, env: Envelope) -> None:
    state.sim_prompt = env["payload"].get("prompt", "")  # type: ignore[attr-defined]
    state.emit("designer.heard_prompt", {"prompt_length": len(state.sim_prompt)})  # type: ignore[attr-defined]


def _on_phase_tick(state: WorkerState, env: Envelope) -> None:
    phase = env["payload"].get("phase")
    if phase != Phase.BOUNTY_DESIGN:
        return
    if state.posted:  # type: ignore[attr-defined]
        return

    topo = state.client.get_topology()
    sponsor = sponsor_for_peer_id(topo.our_public_key)
    state.emit("designer.composing", {"sponsor": sponsor["name"]})

    payload = propose_bounty(
        sim_prompt=state.sim_prompt,  # type: ignore[attr-defined]
        sender_peer_id=topo.our_public_key,
        emit=state.emit,
    )
    payload.setdefault("id", f"bnt_{secrets.token_hex(3)}")

    bounty_env = make_envelope(
        type="bounty.posted",
        round=Phase.BOUNTY_DESIGN,
        sender_id=topo.our_public_key,
        payload=payload,
    )
    wire = encode_envelope(bounty_env)
    # Re-broadcast a few times so peers whose Yggdrasil tree has not yet
    # propagated still hear us. The AXL recv queue is bounded (~100), so we
    # avoid flooding; gossip from receivers carries the rest.
    sent = state.fanout(wire, repeats=4, interval=2.0)

    state.posted = True  # type: ignore[attr-defined]
    # Emit the full envelope payload so the orchestrator's log tailer
    # can hand it to the snapshot accumulator. Diagnostic counts go on a
    # second `*.broadcast` event so they do not pollute the snapshot view.
    state.emit("bounty.posted", {**payload, "sponsor_peer_id": topo.our_public_key})
    state.emit(
        "bounty.broadcast",
        {
            "id": payload["id"],
            "sent_to_initial": sent,
            "rebroadcasts_scheduled": 4,
        },
    )
