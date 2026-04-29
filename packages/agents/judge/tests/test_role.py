"""Judge run-loop handler tests."""

from __future__ import annotations

import json

import pytest

from packages.agents._runtime import WorkerState
from packages.agents.judge.role import (
    _on_bounty_posted,
    _on_phase_tick,
    _on_project_submitted,
)
from packages.axl_client.tests._fake_axl import FakeAxl
from packages.protocol import Phase, decode_envelope, encode_envelope, make_envelope
from packages.skills.hacksim_network.hacksim_network import SkillContext


PEER_A = "a" * 64
PEER_B = "b" * 64
OUR = "f" * 64


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
    monkeypatch.setenv("HACKSIM_ROLE", "judge")
    monkeypatch.setenv("HACKSIM_SIM_ID", "sim_test")
    ctx = SkillContext.from_env()
    s = WorkerState(ctx=ctx, client=ctx.client())
    s.bounties = {}  # type: ignore[attr-defined]
    s.projects = {}  # type: ignore[attr-defined]
    s.scored = set()  # type: ignore[attr-defined]
    s.rubric_published = False  # type: ignore[attr-defined]
    return s


def _bounty_env(*, bid="bnt_1", sender=PEER_A):
    return make_envelope(
        type="bounty.posted",
        round=Phase.BOUNTY_DESIGN,
        sender_id=sender,
        payload={
            "id": bid,
            "title": "Best Visualisation Tool",
            "sponsor_name": "FoldLab",
            "qualification": ["uses real data"],
        },
    )


def _project_env(*, pid, sender=PEER_B, bounty_id="bnt_1"):
    return make_envelope(
        type="project.submitted",
        round=Phase.BUILD,
        sender_id=sender,
        payload={
            "id": pid,
            "project_id": pid,
            "team_id": f"team_{pid}",
            "bounty_id": bounty_id,
            "title": f"Project {pid}",
            "tagline": "demo",
            "commit_hash": "abcd123",
            "entry_path": "index.html",
            "working_dir": "/tmp/x",
        },
    )


class TestAccumulation:
    def test_bounty_added_to_inbox(self, state):
        _on_bounty_posted(state, _bounty_env())
        assert "bnt_1" in state.bounties  # type: ignore[attr-defined]

    def test_project_added_to_inbox(self, state, capsys):
        _on_project_submitted(state, _project_env(pid="proj_a"))
        assert "proj_a" in state.projects  # type: ignore[attr-defined]
        out_types = [json.loads(line)["type"] for line in capsys.readouterr().out.splitlines()]
        assert "judge.heard_project" in out_types

    def test_duplicate_project_ignored(self, state):
        _on_project_submitted(state, _project_env(pid="proj_a"))
        _on_project_submitted(state, _project_env(pid="proj_a"))
        assert len(state.projects) == 1  # type: ignore[attr-defined]


class TestJudging:
    def test_no_op_outside_judging_phase(self, state, fake):
        _on_project_submitted(state, _project_env(pid="proj_a"))
        env = make_envelope(
            type="phase.tick",
            round=Phase.BUILD,
            sender_id=PEER_A,
            payload={"phase": Phase.BUILD},
        )
        _on_phase_tick(state, env)
        assert fake.state.sent == []

    def test_publishes_rubric_then_verdicts(self, state, fake, capsys):
        # Two projects in the inbox, one bounty.
        _on_bounty_posted(state, _bounty_env(bid="bnt_1"))
        _on_project_submitted(state, _project_env(pid="proj_a", bounty_id="bnt_1"))
        _on_project_submitted(state, _project_env(pid="proj_b", bounty_id="bnt_1"))

        env = make_envelope(
            type="phase.tick",
            round=Phase.JUDGING,
            sender_id=PEER_A,
            payload={"phase": Phase.JUDGING},
        )
        _on_phase_tick(state, env)

        # 2 peers in topology, 3 broadcasts (rubric + 2 verdicts) = 6 sends
        assert len(fake.state.sent) == 6

        types = []
        for _peer, _ctype, body in fake.state.sent:
            decoded = decode_envelope(body)
            types.append(decoded["type"])
        assert types.count("rubric.published") == 2
        assert types.count("verdict.published") == 4

        out_types = [json.loads(line)["type"] for line in capsys.readouterr().out.splitlines()]
        assert "rubric.published" in out_types
        assert out_types.count("verdict.published") == 2

    def test_does_not_re_score_same_project(self, state, fake):
        _on_project_submitted(state, _project_env(pid="proj_a"))
        env = make_envelope(
            type="phase.tick",
            round=Phase.JUDGING,
            sender_id=PEER_A,
            payload={"phase": Phase.JUDGING},
        )
        _on_phase_tick(state, env)
        first = len(fake.state.sent)
        _on_phase_tick(state, env)
        # Second call should not add new verdict broadcasts (rubric also stays once).
        assert len(fake.state.sent) == first

    def test_no_projects_emits_no_projects(self, state, fake, capsys):
        env = make_envelope(
            type="phase.tick",
            round=Phase.JUDGING,
            sender_id=PEER_A,
            payload={"phase": Phase.JUDGING},
        )
        _on_phase_tick(state, env)
        out_types = [json.loads(line)["type"] for line in capsys.readouterr().out.splitlines()]
        assert "judge.no_projects" in out_types
