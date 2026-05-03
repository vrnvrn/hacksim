"""Test that the BountyDesigner run loop emits a bounty.posted event
on phase tick to BOUNTY_DESIGN, and only once per phase.
"""

from __future__ import annotations

import json

import pytest

from packages.agents._runtime import WorkerState
from packages.agents.bounty_designer.role import _on_phase_tick, _on_sim_prompt
from packages.axl_client.tests._fake_axl import FakeAxl
from packages.protocol import Phase, decode_envelope, make_envelope
from packages.skills.hacksim_network.hacksim_network import SkillContext

PEER_A = "a" * 64
PEER_B = "b" * 64
OUR = "0" * 64


@pytest.fixture
def fake() -> FakeAxl:
    with FakeAxl() as f:
        f.state.topology = {
            "our_public_key": OUR,
            "peers": [{"public_key": PEER_A, "up": True}],
            "tree": [{"public_key": PEER_A}, {"public_key": PEER_B}],
        }
        yield f


@pytest.fixture
def state(fake, monkeypatch) -> WorkerState:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("AXL_API_PORT", str(fake._server.server_address[1]))
    monkeypatch.setenv("HACKSIM_ROLE", "bounty_designer")
    monkeypatch.setenv("HACKSIM_SIM_ID", "sim_test")
    ctx = SkillContext.from_env()
    s = WorkerState(ctx=ctx, client=ctx.client())
    s.posted = False  # type: ignore[attr-defined]
    s.sim_prompt = "a research hackathon"  # type: ignore[attr-defined]
    return s


class TestPhaseTickHandler:
    def test_posts_bounty_on_bounty_design_phase(self, state, fake, capsys):
        env = make_envelope(
            type="phase.tick",
            round=Phase.BOUNTY_DESIGN,
            sender_id=PEER_A,
            payload={"phase": Phase.BOUNTY_DESIGN},
        )
        _on_phase_tick(state, env)

        # Two peers visible in topology, so two /send calls.
        assert len(fake.state.sent) == 2
        for _peer, _ctype, body in fake.state.sent:
            decoded = decode_envelope(body)
            assert decoded["type"] == "bounty.posted"
            assert decoded["sender_id"] == OUR
            assert "title" in decoded["payload"]
            assert "sponsor_name" in decoded["payload"]
            assert isinstance(decoded["payload"]["prize_amount_usd"], int)

        # State recorded the post; emit produced a bounty.posted line.
        assert state.posted is True  # type: ignore[attr-defined]
        out = capsys.readouterr().out.splitlines()
        types = [json.loads(line)["type"] for line in out]
        assert "designer.composing" in types
        assert "bounty.posted" in types

    def test_ignores_non_bounty_phases(self, state, fake):
        env = make_envelope(
            type="phase.tick",
            round=Phase.BUILD,
            sender_id=PEER_A,
            payload={"phase": Phase.BUILD},
        )
        _on_phase_tick(state, env)
        assert fake.state.sent == []
        assert state.posted is False  # type: ignore[attr-defined]

    def test_only_posts_once_per_phase(self, state, fake):
        env = make_envelope(
            type="phase.tick",
            round=Phase.BOUNTY_DESIGN,
            sender_id=PEER_A,
            payload={"phase": Phase.BOUNTY_DESIGN},
        )
        _on_phase_tick(state, env)
        first_count = len(fake.state.sent)
        _on_phase_tick(state, env)
        # Second call should not add more sends.
        assert len(fake.state.sent) == first_count


class TestSimPromptHandler:
    def test_sim_prompt_envelope_updates_state(self, state):
        env = make_envelope(
            type="sim.created" if False else "phase.tick",
            round=0,
            sender_id=PEER_A,
            payload={"prompt": "a brand new prompt about bees"},
        )
        # We bypass the type check for this unit test by calling directly.
        _on_sim_prompt(state, env)
        assert state.sim_prompt == "a brand new prompt about bees"  # type: ignore[attr-defined]
