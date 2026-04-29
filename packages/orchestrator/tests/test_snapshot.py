"""Tests for the snapshot accumulator."""

from __future__ import annotations

from packages.orchestrator.snapshot import (
    apply_event,
    apply_events,
    empty_snapshot,
)
from packages.protocol import Phase


def _new() -> dict:
    return empty_snapshot(
        sim_id="sim_x",
        prompt="a research hackathon",
        config={"builders": 4, "judges": 2, "designers": 2, "duration_hint": "short"},
        created_at="2026-04-29T00:00:00Z",
    )


class TestEmpty:
    def test_initial_arrays_are_empty(self):
        snap = _new()
        assert snap["bounties"] == []
        assert snap["builders"] == []
        assert snap["teams"] == []
        assert snap["projects"] == []
        assert snap["judges"] == []
        assert snap["verdicts"] == []
        assert snap["phase"] == 0


class TestPhaseTick:
    def test_phase_advances(self):
        snap = apply_event(_new(), "phase.tick", {"phase": Phase.BUILD})
        assert snap["phase"] == Phase.BUILD

    def test_invalid_phase_ignored(self):
        snap = apply_event(_new(), "phase.tick", {"phase": "garbage"})
        assert snap["phase"] == 0


class TestBountyPosted:
    def test_appends_bounty(self):
        snap = apply_event(
            _new(),
            "bounty.posted",
            {
                "id": "bnt_1",
                "title": "Privacy Demo",
                "sponsor_name": "Atlas",
                "prize_amount_usd": 2000,
                "description": "...",
                "qualification": ["a", "b"],
            },
        )
        assert len(snap["bounties"]) == 1
        b = snap["bounties"][0]
        assert b["id"] == "bnt_1"
        assert b["title"] == "Privacy Demo"
        assert b["prize_amount_usd"] == 2000
        assert b["qualification"] == ["a", "b"]

    def test_dedup_by_id(self):
        snap = apply_events(
            _new(),
            [
                ("bounty.posted", {"id": "bnt_1", "title": "X"}),
                ("bounty.posted", {"id": "bnt_1", "title": "Y"}),
            ],
        )
        assert len(snap["bounties"]) == 1
        assert snap["bounties"][0]["title"] == "X"

    def test_missing_id_ignored(self):
        snap = apply_event(_new(), "bounty.posted", {"title": "no id"})
        assert snap["bounties"] == []


class TestTeamFormed:
    def test_appends_team_and_updates_builder(self):
        snap = apply_events(
            _new(),
            [
                ("builder.registered", {"peer_id": "a" * 64, "display_name": "B-aaaa", "skills": ["Python"]}),
                ("team.formed", {"id": "team_1", "bounty_id": "bnt_1", "members": ["a" * 64]}),
            ],
        )
        assert len(snap["teams"]) == 1
        builder = snap["builders"][0]
        assert builder["team_id"] == "team_1"
        assert builder["current_bounty_id"] == "bnt_1"

    def test_dedup_by_id(self):
        snap = apply_events(
            _new(),
            [
                ("team.formed", {"id": "team_1", "bounty_id": "bnt_1", "members": []}),
                ("team.formed", {"id": "team_1", "bounty_id": "bnt_2", "members": []}),
            ],
        )
        assert len(snap["teams"]) == 1
        assert snap["teams"][0]["bounty_id"] == "bnt_1"


class TestProjectSubmitted:
    def test_appends_project(self):
        snap = apply_event(
            _new(),
            "project.submitted",
            {
                "project_id": "proj_a",
                "team_id": "team_1",
                "bounty_id": "bnt_1",
                "title": "FoldLens",
                "tagline": "demo",
                "commit_hash": "abc123",
                "entry_path": "index.html",
            },
        )
        p = snap["projects"][0]
        assert p["id"] == "proj_a"
        assert p["title"] == "FoldLens"
        assert p["status"] == "submitted"
        assert p["commit_hash"] == "abc123"
        assert p["artefact_path"] == "served"

    def test_dedup_by_project_id(self):
        snap = apply_events(
            _new(),
            [
                ("project.submitted", {"project_id": "p", "title": "first"}),
                ("project.submitted", {"project_id": "p", "title": "second"}),
            ],
        )
        assert len(snap["projects"]) == 1
        assert snap["projects"][0]["title"] == "first"


class TestRubricPublished:
    def test_creates_judge_row(self):
        snap = apply_event(
            _new(),
            "rubric.published",
            {
                "judge_peer_id": "j" * 64,
                "judge_name": "J-jjjj",
                "rubric": [
                    {"name": "novelty", "weight": 0.5, "description": "originality"},
                    {"name": "depth", "weight": 0.5, "description": "engineering"},
                ],
            },
        )
        assert len(snap["judges"]) == 1
        j = snap["judges"][0]
        assert j["peer_id"] == "j" * 64
        assert j["display_name"] == "J-jjjj"
        assert len(j["rubric"]) == 2

    def test_re_publish_updates_rubric(self):
        snap = apply_events(
            _new(),
            [
                ("rubric.published", {"judge_peer_id": "j" * 64, "rubric": [{"name": "n", "weight": 1, "description": "a"}]}),
                ("rubric.published", {"judge_peer_id": "j" * 64, "rubric": [{"name": "x", "weight": 1, "description": "b"}]}),
            ],
        )
        assert len(snap["judges"]) == 1
        assert snap["judges"][0]["rubric"][0]["name"] == "x"


class TestVerdictPublished:
    def test_appends_verdict_and_updates_judge_count(self):
        snap = apply_events(
            _new(),
            [
                ("rubric.published", {"judge_peer_id": "j" * 64, "rubric": []}),
                ("project.submitted", {"project_id": "p1"}),
                (
                    "verdict.published",
                    {
                        "project_id": "p1",
                        "judge_peer_id": "j" * 64,
                        "scores": {"novelty": 7},
                        "total": 7.0,
                        "feedback": "nice",
                    },
                ),
            ],
        )
        assert len(snap["verdicts"]) == 1
        assert snap["judges"][0]["scored_count"] == 1
        assert snap["judges"][0]["total_to_score"] == 1
        # Project status flips to judged.
        assert snap["projects"][0]["status"] == "judged"

    def test_dedup_one_judge_per_project(self):
        snap = apply_events(
            _new(),
            [
                ("verdict.published", {"project_id": "p1", "judge_peer_id": "j" * 64, "total": 5.0}),
                ("verdict.published", {"project_id": "p1", "judge_peer_id": "j" * 64, "total": 9.0}),
            ],
        )
        assert len(snap["verdicts"]) == 1
        assert snap["verdicts"][0]["total"] == 5.0


class TestHackathonClosed:
    def test_phase_advances_to_showcase_with_leaderboard(self):
        snap = apply_event(
            _new(),
            "hackathon.closed",
            {
                "leaderboard": [
                    {"rank": 1, "project_id": "p1", "title": "A", "total_score": 8.5},
                    {"rank": 2, "project_id": "p2", "title": "B", "total_score": 7.0},
                ],
            },
        )
        assert snap["phase"] == Phase.SHOWCASE
        assert snap["leaderboard"][0]["rank"] == 1


class TestBuilderRegistered:
    def test_appends_builder(self):
        snap = apply_event(
            _new(),
            "builder.registered",
            {"peer_id": "b" * 64, "display_name": "B-bbbb", "skills": ["Python", "viz"]},
        )
        assert len(snap["builders"]) == 1
        assert snap["builders"][0]["skills"] == ["Python", "viz"]

    def test_dedup_by_peer_id(self):
        snap = apply_events(
            _new(),
            [
                ("builder.registered", {"peer_id": "b" * 64}),
                ("builder.registered", {"peer_id": "b" * 64, "display_name": "another"}),
            ],
        )
        assert len(snap["builders"]) == 1


class TestUnknownEvent:
    def test_pass_through(self):
        snap = apply_event(_new(), "designer.composing", {"sponsor": "x"})
        assert snap["bounties"] == []
        assert snap["phase"] == 0


class TestApplyIsPure:
    def test_input_not_mutated(self):
        before = _new()
        before_copy = empty_snapshot(
            sim_id="sim_x",
            prompt="a research hackathon",
            config={"builders": 4, "judges": 2, "designers": 2, "duration_hint": "short"},
            created_at="2026-04-29T00:00:00Z",
        )
        _ = apply_event(before, "bounty.posted", {"id": "x", "title": "y"})
        assert before == before_copy
