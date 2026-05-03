"""Tests for builder decision logic: skill-bounty fit and pick."""

from __future__ import annotations

import pytest

from packages.agents.builder.decisions import pick_bounty, score_bounty_fit
from packages.agents.builder.persona import (
    PROFILE_SIZE,
    SKILL_POOL,
    skill_profile_for_peer_id,
)

PEER_A = "a" * 64


@pytest.fixture(autouse=True)
def _no_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def _bounty(**fields):
    base = {
        "id": "bnt_x",
        "title": "Bounty",
        "sponsor_name": "X",
        "description": "Build something.",
        "qualification": ["working demo"],
        "prize_amount_usd": 1000,
    }
    base.update(fields)
    return base


class TestSkillProfile:
    def test_profile_size(self):
        profile = skill_profile_for_peer_id(PEER_A)
        assert len(profile) == PROFILE_SIZE

    def test_profile_skills_in_pool(self):
        profile = skill_profile_for_peer_id(PEER_A)
        for skill in profile:
            assert skill in SKILL_POOL

    def test_profile_has_no_duplicates(self):
        profile = skill_profile_for_peer_id(PEER_A)
        assert len(profile) == len(set(profile))

    def test_profile_is_deterministic(self):
        a = skill_profile_for_peer_id(PEER_A)
        b = skill_profile_for_peer_id(PEER_A)
        assert a == b


class TestScoreBountyFit:
    def test_skill_in_description_increases_score(self):
        bounty = _bounty(description="Build a Python visualisation tool")
        s_with = score_bounty_fit(bounty=bounty, skills=["Python", "viz"])
        s_without = score_bounty_fit(bounty=bounty, skills=["Cairo", "Move"])
        assert s_with > s_without

    def test_skill_in_qualification_increases_score(self):
        bounty = _bounty(
            qualification=["uses ZK proofs", "has frontend", "ships demo"],
        )
        s = score_bounty_fit(bounty=bounty, skills=["ZK", "frontend"])
        assert s >= 4  # both skills hit, with the case-insensitive token match bonus

    def test_no_overlap_returns_zero(self):
        bounty = _bounty(
            description="biology and chemistry experiments",
            qualification=["uses a wet lab"],
        )
        s = score_bounty_fit(bounty=bounty, skills=["Solidity"])
        assert s == 0


class TestPickBounty:
    def test_empty_returns_none(self):
        assert pick_bounty(bounties=[], skills=["Python"]) is None

    def test_picks_higher_score(self):
        a = _bounty(id="bnt_a", title="Solidity bounty", description="ZK and Solidity work")
        b = _bounty(id="bnt_b", title="Bio bounty", description="biology lab")
        chosen = pick_bounty(bounties=[a, b], skills=["Solidity", "ZK"])
        assert chosen["id"] == "bnt_a"

    def test_breaks_tie_alphabetically(self):
        a = _bounty(id="bnt_a", title="Beta bounty")
        b = _bounty(id="bnt_b", title="Alpha bounty")
        # No skills overlap with either, so both score 0; picker picks alphabetically.
        chosen = pick_bounty(bounties=[a, b], skills=["Cairo"])
        assert chosen["title"] == "Alpha bounty"

    def test_returns_one_of_inputs(self):
        a = _bounty(id="bnt_a")
        b = _bounty(id="bnt_b")
        chosen = pick_bounty(bounties=[a, b], skills=["Python"])
        assert chosen is a or chosen is b
