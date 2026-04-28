"""Builder run-loop handler tests."""

from __future__ import annotations

import json

import pytest

from packages.agents._runtime import WorkerState
from packages.agents.builder.role import _on_bounty_posted, _on_phase_tick
from packages.axl_client.tests._fake_axl import FakeAxl
from packages.protocol import Phase, decode_envelope, encode_envelope, make_envelope
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
    monkeypatch.setenv("HACKSIM_ROLE", "builder")
    monkeypatch.setenv("HACKSIM_SIM_ID", "sim_test")
    ctx = SkillContext.from_env()
    s = WorkerState(ctx=ctx, client=ctx.client())
    s.bounties = {}  # type: ignore[attr-defined]
    s.team_formed = False  # type: ignore[attr-defined]
    s.chosen_bounty = None  # type: ignore[attr-defined]
    s.team_id = None  # type: ignore[attr-defined]
    return s


def _bounty_envelope(*, bid: str, title: str, sender: str) -> dict:
    return make_envelope(
        type="bounty.posted",
        round=Phase.BOUNTY_DESIGN,
        sender_id=sender,
        payload={
            "id": bid,
            "title": title,
            "sponsor_name": "TestSponsor",
            "prize_amount_usd": 1000,
            "description": "Build a Python web demo.",
            "qualification": ["uses Python"],
        },
    )


class TestBountyAccumulation:
    def test_bounty_added_to_inbox(self, state):
        env = _bounty_envelope(bid="bnt_1", title="A", sender=PEER_A)
        _on_bounty_posted(state, env)
        assert "bnt_1" in state.bounties  # type: ignore[attr-defined]

    def test_duplicate_bounty_id_ignored(self, state):
        e1 = _bounty_envelope(bid="bnt_1", title="A", sender=PEER_A)
        e2 = _bounty_envelope(bid="bnt_1", title="A again", sender=PEER_B)
        _on_bounty_posted(state, e1)
        _on_bounty_posted(state, e2)
        assert len(state.bounties) == 1  # type: ignore[attr-defined]

    def test_envelope_without_id_ignored(self, state):
        env = make_envelope(
            type="bounty.posted",
            round=Phase.BOUNTY_DESIGN,
            sender_id=PEER_A,
            payload={"title": "A"},  # no id field
        )
        _on_bounty_posted(state, env)
        assert state.bounties == {}  # type: ignore[attr-defined]


class TestTeamFormation:
    def test_no_op_outside_team_formation_phase(self, state, fake):
        env = make_envelope(
            type="phase.tick",
            round=Phase.BUILD,
            sender_id=PEER_A,
            payload={"phase": Phase.BUILD},
        )
        _on_phase_tick(state, env)
        assert fake.state.sent == []
        assert state.team_formed is False  # type: ignore[attr-defined]

    def test_no_bounty_emits_no_bounty_event(self, state, fake, capsys):
        env = make_envelope(
            type="phase.tick",
            round=Phase.TEAM_FORMATION,
            sender_id=PEER_A,
            payload={"phase": Phase.TEAM_FORMATION},
        )
        _on_phase_tick(state, env)
        out = capsys.readouterr().out.splitlines()
        types = [json.loads(line)["type"] for line in out]
        assert "builder.no_bounty" in types
        assert fake.state.sent == []

    def test_picks_and_broadcasts_team_formed(self, state, fake, capsys):
        # Drop two bounties into the inbox.
        for i, bid in enumerate(["bnt_1", "bnt_2"]):
            _on_bounty_posted(state, _bounty_envelope(bid=bid, title=f"T{i}", sender=PEER_A))

        env = make_envelope(
            type="phase.tick",
            round=Phase.TEAM_FORMATION,
            sender_id=PEER_A,
            payload={"phase": Phase.TEAM_FORMATION},
        )
        _on_phase_tick(state, env)

        # Sent to the two peers visible in topology.
        assert len(fake.state.sent) == 2
        for _peer, _ctype, body in fake.state.sent:
            decoded = decode_envelope(body)
            assert decoded["type"] == "team.formed"
            assert decoded["sender_id"] == OUR
            assert decoded["payload"]["bounty_id"] in {"bnt_1", "bnt_2"}
            assert decoded["payload"]["members"] == [OUR]
            assert decoded["payload"]["team_id"].startswith("team_")

        assert state.team_formed is True  # type: ignore[attr-defined]
        assert state.chosen_bounty is not None  # type: ignore[attr-defined]

        out_types = [json.loads(line)["type"] for line in capsys.readouterr().out.splitlines()]
        assert "team.formed" in out_types

    def test_does_not_form_team_twice(self, state, fake):
        _on_bounty_posted(state, _bounty_envelope(bid="bnt_1", title="A", sender=PEER_A))
        env = make_envelope(
            type="phase.tick",
            round=Phase.TEAM_FORMATION,
            sender_id=PEER_A,
            payload={"phase": Phase.TEAM_FORMATION},
        )
        _on_phase_tick(state, env)
        first_count = len(fake.state.sent)
        _on_phase_tick(state, env)
        assert len(fake.state.sent) == first_count
