"""Organiser role-handler tests.

We invoke handlers and timer functions directly so the test does not
depend on a long-running event loop.
"""

from __future__ import annotations

import json

import pytest

from packages.agents._runtime import WorkerState
from packages.agents.organiser.role import (
    _close_hackathon,
    _make_phase_emitter,
    _on_project_submitted,
    _on_verdict_published,
)
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
    monkeypatch.setenv("HACKSIM_ROLE", "organiser")
    monkeypatch.setenv("HACKSIM_SIM_ID", "sim_test")
    ctx = SkillContext.from_env()
    s = WorkerState(ctx=ctx, client=ctx.client())
    s.projects = {}  # type: ignore[attr-defined]
    s.verdicts = {}  # type: ignore[attr-defined]
    s.closed_emitted = False  # type: ignore[attr-defined]
    return s


def _project_env(*, pid="proj_a", title="Demo", team="team_x", bounty="bnt_1"):
    return make_envelope(
        type="project.submitted",
        round=Phase.BUILD,
        sender_id=PEER_A,
        payload={
            "id": pid,
            "project_id": pid,
            "title": title,
            "team_id": team,
            "bounty_id": bounty,
            "commit_hash": "abc1234",
            "entry_path": "index.html",
            "working_dir": "/tmp/x",
        },
    )


def _verdict_env(*, pid, total, judge=PEER_B):
    return make_envelope(
        type="verdict.published",
        round=Phase.JUDGING,
        sender_id=judge,
        payload={
            "id": f"verdict_{pid}_{judge[:8]}",
            "project_id": pid,
            "judge_peer_id": judge,
            "scores": {"novelty": 7, "technical_depth": 7, "demo_quality": 7, "documentation": 7, "bounty_fit": 7},
            "total": total,
            "feedback": "ok",
        },
    )


class TestProjectAccumulation:
    def test_first_project_added(self, state):
        _on_project_submitted(state, _project_env(pid="proj_a"))
        assert "proj_a" in state.projects  # type: ignore[attr-defined]

    def test_duplicate_project_ignored(self, state):
        _on_project_submitted(state, _project_env(pid="proj_a"))
        _on_project_submitted(state, _project_env(pid="proj_a", title="changed"))
        assert state.projects["proj_a"]["title"] == "Demo"  # type: ignore[attr-defined]


class TestVerdictAccumulation:
    def test_verdict_grouped_by_project(self, state):
        _on_verdict_published(state, _verdict_env(pid="proj_a", total=7.0, judge=PEER_A))
        _on_verdict_published(state, _verdict_env(pid="proj_a", total=8.0, judge=PEER_B))
        assert len(state.verdicts["proj_a"]) == 2  # type: ignore[attr-defined]

    def test_judge_dedupe_per_project(self, state):
        _on_verdict_published(state, _verdict_env(pid="proj_a", total=7.0, judge=PEER_A))
        _on_verdict_published(state, _verdict_env(pid="proj_a", total=99.0, judge=PEER_A))
        assert len(state.verdicts["proj_a"]) == 1  # type: ignore[attr-defined]
        assert list(state.verdicts["proj_a"].values())[0]["total"] == 7.0  # type: ignore[attr-defined]


class TestPhaseEmitter:
    def test_phase_tick_broadcast(self, state, fake, capsys):
        emit = _make_phase_emitter(Phase.BOUNTY_DESIGN)
        emit(state)
        # 2 peers in topology => 2 sends.
        assert len(fake.state.sent) == 2
        for _peer, _ctype, body in fake.state.sent:
            decoded = decode_envelope(body)
            assert decoded["type"] == "phase.tick"
            assert decoded["payload"]["phase"] == Phase.BOUNTY_DESIGN
        out_types = [json.loads(line)["type"] for line in capsys.readouterr().out.splitlines()]
        assert "phase.tick.broadcast" in out_types


class TestCloseHackathon:
    def test_emits_hackathon_closed_with_leaderboard(self, state, fake, capsys):
        _on_project_submitted(state, _project_env(pid="proj_a"))
        _on_project_submitted(state, _project_env(pid="proj_b"))
        _on_verdict_published(state, _verdict_env(pid="proj_a", total=8.0, judge=PEER_A))
        _on_verdict_published(state, _verdict_env(pid="proj_a", total=7.0, judge=PEER_B))
        _on_verdict_published(state, _verdict_env(pid="proj_b", total=6.0, judge=PEER_A))

        _close_hackathon(state)

        # 2 peers in topology => 2 sends.
        assert len(fake.state.sent) == 2
        decoded = decode_envelope(fake.state.sent[0][2])
        assert decoded["type"] == "hackathon.closed"
        leaderboard = decoded["payload"]["leaderboard"]
        assert leaderboard[0]["project_id"] == "proj_a"  # higher avg score
        assert leaderboard[0]["total_score"] == 7.5
        assert leaderboard[1]["project_id"] == "proj_b"
        assert state.closed_emitted is True  # type: ignore[attr-defined]

        out = capsys.readouterr().out.splitlines()
        types = [json.loads(line)["type"] for line in out]
        assert "hackathon.closed" in types

    def test_close_idempotent(self, state, fake):
        _close_hackathon(state)
        first = len(fake.state.sent)
        _close_hackathon(state)
        assert len(fake.state.sent) == first
