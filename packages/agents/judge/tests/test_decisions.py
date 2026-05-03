"""Tests for Judge decision logic."""

from __future__ import annotations

import pytest

from packages.agents.judge.decisions import _score_stub, score_project
from packages.agents.judge.persona import (
    ARCHETYPES,
    CRITERIA,
    archetype_for_peer_id,
)

PEER_J1 = "1" * 64
PEER_J2 = "2" * 64
PEER_J3 = "3" * 64
PEER_J4 = "4" * 64


@pytest.fixture(autouse=True)
def _no_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def _project(**fields):
    base = {
        "project_id": "proj_x",
        "title": "FoldLens",
        "tagline": "interactive viewer",
        "commit_hash": "abc1234",
        "entry_path": "index.html",
    }
    base.update(fields)
    return base


def _bounty(**fields):
    base = {
        "id": "bnt_1",
        "title": "Best Visualisation Tool",
        "sponsor_name": "FoldLab",
        "qualification": ["uses real data"],
    }
    base.update(fields)
    return base


class TestArchetype:
    def test_archetype_is_deterministic(self):
        assert archetype_for_peer_id(PEER_J1) == archetype_for_peer_id(PEER_J1)

    def test_archetypes_in_known_set(self):
        names = {a["name"] for a in ARCHETYPES}
        assert archetype_for_peer_id(PEER_J1)["name"] in names

    def test_weights_sum_to_one(self):
        for arc in ARCHETYPES:
            total = sum(arc["weights"])
            assert abs(total - 1.0) < 1e-9, f"{arc['name']}: {total}"


class TestStubScore:
    def test_returns_full_verdict_shape(self):
        v = _score_stub(project=_project(), bounty=_bounty(), judge_peer_id=PEER_J1)
        assert set(v.keys()) >= {
            "project_id",
            "judge_peer_id",
            "scores",
            "total",
            "feedback",
            "archetype",
        }
        for crit in CRITERIA:
            assert crit in v["scores"]
            assert 0 <= v["scores"][crit] <= 10

    def test_total_in_range(self):
        v = _score_stub(project=_project(), bounty=_bounty(), judge_peer_id=PEER_J1)
        assert 0.0 <= v["total"] <= 10.0

    def test_total_matches_weighted_sum(self):
        v = _score_stub(project=_project(), bounty=_bounty(), judge_peer_id=PEER_J1)
        archetype = archetype_for_peer_id(PEER_J1)
        expected = sum(v["scores"][crit] * w for crit, w in zip(CRITERIA, archetype["weights"], strict=True))
        assert abs(v["total"] - round(expected, 2)) < 1e-9

    def test_score_is_deterministic_per_judge_per_project(self):
        a = _score_stub(project=_project(), bounty=_bounty(), judge_peer_id=PEER_J1)
        b = _score_stub(project=_project(), bounty=_bounty(), judge_peer_id=PEER_J1)
        assert a["scores"] == b["scores"]
        assert a["total"] == b["total"]

    def test_two_judges_diverge_on_same_project(self):
        a = _score_stub(project=_project(), bounty=_bounty(), judge_peer_id=PEER_J1)
        b = _score_stub(project=_project(), bounty=_bounty(), judge_peer_id=PEER_J2)
        # At least one criterion differs.
        assert a["scores"] != b["scores"] or a["total"] != b["total"]

    def test_one_judge_diverges_across_projects(self):
        a = _score_stub(
            project=_project(project_id="proj_a"), bounty=_bounty(), judge_peer_id=PEER_J1
        )
        b = _score_stub(
            project=_project(project_id="proj_b"), bounty=_bounty(), judge_peer_id=PEER_J1
        )
        assert a["scores"] != b["scores"] or a["total"] != b["total"]

    def test_works_with_no_bounty(self):
        v = _score_stub(project=_project(), bounty=None, judge_peer_id=PEER_J1)
        assert "scores" in v and "total" in v

    def test_feedback_mentions_project_or_bounty(self):
        v = _score_stub(
            project=_project(title="FoldLens"),
            bounty=_bounty(title="Best Visualisation Tool"),
            judge_peer_id=PEER_J1,
        )
        text = v["feedback"]
        assert "FoldLens" in text or "Visualisation" in text


class TestScoreProject:
    def test_falls_back_to_stub_without_api_key(self):
        v = score_project(project=_project(), bounty=_bounty(), judge_peer_id=PEER_J1)
        assert "scores" in v and isinstance(v["total"], float)
