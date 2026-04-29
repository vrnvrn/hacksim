"""Tests for the leaderboard tally."""

from __future__ import annotations

from packages.agents.organiser.tally import tally_leaderboard


def _project(pid: str, **fields):
    base = {"title": f"Project {pid}", "team_id": f"team_{pid}", "bounty_id": "bnt_1"}
    base.update(fields)
    return {"project_id": pid, **base}


def _verdict(pid: str, total: float, judge: str = "j1"):
    return {"project_id": pid, "judge_peer_id": judge, "total": total}


def test_empty_inputs_return_empty_list():
    assert tally_leaderboard(projects={}, verdicts_by_project={}) == []


def test_single_project_no_verdicts():
    rows = tally_leaderboard(
        projects={"p1": _project("p1")},
        verdicts_by_project={},
    )
    assert len(rows) == 1
    assert rows[0]["rank"] == 1
    assert rows[0]["total_score"] == 0.0
    assert rows[0]["verdicts"] == 0


def test_averages_multiple_verdicts():
    rows = tally_leaderboard(
        projects={"p1": _project("p1")},
        verdicts_by_project={
            "p1": [_verdict("p1", 6.0, "j1"), _verdict("p1", 8.0, "j2"), _verdict("p1", 7.0, "j3")],
        },
    )
    assert rows[0]["total_score"] == 7.0
    assert rows[0]["verdicts"] == 3


def test_ranks_descending_by_score():
    rows = tally_leaderboard(
        projects={"p1": _project("p1"), "p2": _project("p2"), "p3": _project("p3")},
        verdicts_by_project={
            "p1": [_verdict("p1", 5.0)],
            "p2": [_verdict("p2", 8.0)],
            "p3": [_verdict("p3", 6.5)],
        },
    )
    pids_by_rank = [(r["rank"], r["project_id"]) for r in rows]
    assert pids_by_rank == [(1, "p2"), (2, "p3"), (3, "p1")]


def test_breaks_tie_alphabetically():
    rows = tally_leaderboard(
        projects={"p_b": _project("p_b"), "p_a": _project("p_a")},
        verdicts_by_project={
            "p_a": [_verdict("p_a", 7.0)],
            "p_b": [_verdict("p_b", 7.0)],
        },
    )
    assert rows[0]["project_id"] == "p_a"
    assert rows[1]["project_id"] == "p_b"


def test_unscored_projects_rank_last():
    rows = tally_leaderboard(
        projects={"p1": _project("p1"), "p2": _project("p2")},
        verdicts_by_project={"p1": [_verdict("p1", 5.0)]},
    )
    assert rows[0]["project_id"] == "p1"
    assert rows[1]["project_id"] == "p2"
    assert rows[1]["total_score"] == 0.0
