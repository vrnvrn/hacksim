"""Tests for the BountyDesigner decision logic.

The stub fallback runs when ANTHROPIC_API_KEY is not set. Tests work in
both modes by clearing the env var.
"""

from __future__ import annotations

import pytest

from packages.agents.bounty_designer.decisions import (
    _parse_bounty_json,
    _propose_stub,
    propose_bounty,
)
from packages.agents.bounty_designer.persona import (
    SPONSORS,
    sponsor_for_peer_id,
)


PEER_A = "a" * 64
PEER_B = "b" * 64


@pytest.fixture(autouse=True)
def _no_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


class TestSponsorPick:
    def test_same_peer_id_picks_same_sponsor(self):
        a = sponsor_for_peer_id(PEER_A)
        b = sponsor_for_peer_id(PEER_A)
        assert a == b

    def test_different_peer_ids_likely_pick_different_sponsors(self):
        picks = {sponsor_for_peer_id(p)["name"] for p in [PEER_A, PEER_B, "c" * 64, "d" * 64]}
        assert len(picks) >= 2

    def test_pick_is_in_known_archetypes(self):
        for peer in [PEER_A, PEER_B, "1" * 64, "f" * 64]:
            sponsor = sponsor_for_peer_id(peer)
            assert sponsor["name"] in {s["name"] for s in SPONSORS}


class TestStubBounty:
    def test_stub_returns_full_shape(self):
        b = _propose_stub(sim_prompt="a research hackathon", sender_peer_id=PEER_A)
        assert set(b.keys()) >= {
            "title",
            "sponsor_name",
            "prize_amount_usd",
            "description",
            "qualification",
        }
        assert isinstance(b["prize_amount_usd"], int)
        assert b["prize_amount_usd"] > 0
        assert isinstance(b["qualification"], list) and len(b["qualification"]) >= 2
        assert isinstance(b["description"], str) and len(b["description"]) > 50

    def test_stub_prize_within_tier(self):
        b = _propose_stub(sim_prompt="x", sender_peer_id=PEER_A)
        assert 100 <= b["prize_amount_usd"] <= 10_000

    def test_stub_is_deterministic(self):
        a = _propose_stub(sim_prompt="x", sender_peer_id=PEER_A)
        b = _propose_stub(sim_prompt="x", sender_peer_id=PEER_A)
        assert a == b

    def test_stub_varies_with_peer(self):
        a = _propose_stub(sim_prompt="x", sender_peer_id=PEER_A)
        b = _propose_stub(sim_prompt="x", sender_peer_id=PEER_B)
        assert a["sponsor_name"] != b["sponsor_name"] or a["title"] != b["title"]

    def test_stub_varies_with_prompt(self):
        a = _propose_stub(sim_prompt="prompt one", sender_peer_id=PEER_A)
        b = _propose_stub(sim_prompt="prompt two completely different", sender_peer_id=PEER_A)
        # Prize amount picks from the same tier list but different index by prompt hash.
        assert a["description"] != b["description"]


class TestProposeBounty:
    def test_falls_back_to_stub_without_api_key(self):
        b = propose_bounty(sim_prompt="test", sender_peer_id=PEER_A)
        assert b["sponsor_name"]
        assert isinstance(b["prize_amount_usd"], int)


class TestParseBountyJson:
    def test_extracts_clean_json(self):
        text = '{"title":"x","sponsor_name":"y","prize_amount_usd":100,"description":"z","qualification":["a"]}'
        b = _parse_bounty_json(text, fallback_sponsor="Y")
        assert b["title"] == "x"

    def test_extracts_json_with_surrounding_prose(self):
        text = (
            "Sure, here is the bounty:\n"
            '{"title":"x","sponsor_name":"y","prize_amount_usd":100,'
            '"description":"z","qualification":["a"]}\n'
            "Hope this helps!"
        )
        b = _parse_bounty_json(text, fallback_sponsor="Y")
        assert b["title"] == "x"

    def test_missing_field_raises(self):
        text = '{"title":"x","prize_amount_usd":100}'
        with pytest.raises(ValueError, match="missing fields"):
            _parse_bounty_json(text, fallback_sponsor="Y")

    def test_no_json_raises(self):
        with pytest.raises(ValueError, match="no JSON"):
            _parse_bounty_json("just prose", fallback_sponsor="Y")

    def test_qualification_not_a_list_raises(self):
        text = '{"title":"x","sponsor_name":"y","prize_amount_usd":1,"description":"z","qualification":"a"}'
        with pytest.raises(ValueError, match="qualification"):
            _parse_bounty_json(text, fallback_sponsor="Y")
