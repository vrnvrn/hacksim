"""Tests for the HackSim wire protocol envelope module."""

from __future__ import annotations

import json

import pytest

from packages.protocol import (
    PROTO_VERSION,
    Envelope,
    Phase,
    decode_envelope,
    encode_envelope,
    is_known_event,
    make_envelope,
)


VALID_PEER = "a" * 64
ALT_PEER = "b" * 64


def _make_sample(**overrides) -> Envelope:
    base = {
        "type": "bounty.posted",
        "round": Phase.BOUNTY_DESIGN,
        "sender_id": VALID_PEER,
        "payload": {"bounty_id": "bnt_1", "title": "FoldLab"},
        "timestamp": 1714305735.0,
    }
    base.update(overrides)
    return make_envelope(**base)


class TestMakeEnvelope:
    def test_minimal_envelope_round_trips(self):
        env = _make_sample()
        assert env["proto"] == PROTO_VERSION
        assert env["type"] == "bounty.posted"
        assert env["round"] == Phase.BOUNTY_DESIGN
        assert env["sender_id"] == VALID_PEER
        assert env["timestamp"] == 1714305735.0
        assert env["payload"] == {"bounty_id": "bnt_1", "title": "FoldLab"}

    def test_unknown_event_type_rejected(self):
        with pytest.raises(ValueError, match="unknown event type"):
            _make_sample(type="bounty.unknown")

    def test_invalid_phase_rejected(self):
        with pytest.raises(ValueError, match="round must be one of"):
            _make_sample(round=99)

    def test_short_sender_id_rejected(self):
        with pytest.raises(ValueError, match="64-character hex"):
            _make_sample(sender_id="abc")

    def test_non_hex_sender_id_rejected(self):
        with pytest.raises(ValueError, match="valid hex"):
            _make_sample(sender_id="z" * 64)

    def test_non_dict_payload_rejected(self):
        with pytest.raises(TypeError):
            _make_sample(payload=["not", "a", "dict"])

    def test_payload_is_copied_not_aliased(self):
        original = {"k": "v"}
        env = _make_sample(payload=original)
        original["k"] = "mutated"
        assert env["payload"] == {"k": "v"}

    def test_default_timestamp_is_current_time(self):
        env = make_envelope(
            type="phase.tick",
            round=Phase.BUILD,
            sender_id=VALID_PEER,
            payload={"phase": Phase.BUILD},
        )
        assert isinstance(env["timestamp"], float)
        assert env["timestamp"] > 0


class TestEncoding:
    def test_envelope_round_trips(self):
        env = _make_sample()
        wire = encode_envelope(env)
        assert isinstance(wire, bytes)
        decoded = decode_envelope(wire)
        assert decoded == env

    def test_encoding_is_utf8_json(self):
        env = _make_sample(payload={"title": "Cafe é"})
        wire = encode_envelope(env)
        as_obj = json.loads(wire.decode("utf-8"))
        assert as_obj["payload"]["title"] == "Cafe é"

    def test_decode_rejects_non_json(self):
        with pytest.raises(ValueError, match="UTF-8 JSON"):
            decode_envelope(b"\xff\xfe\x00")

    def test_decode_rejects_non_object(self):
        with pytest.raises(ValueError, match="JSON object"):
            decode_envelope(b'["array", "not", "object"]')

    def test_decode_rejects_missing_fields(self):
        partial = {"proto": 1, "type": "phase.tick"}
        with pytest.raises(ValueError, match="missing required fields"):
            decode_envelope(json.dumps(partial).encode("utf-8"))

    def test_decode_rejects_wrong_proto_version(self):
        env = _make_sample()
        env["proto"] = 99
        wire = json.dumps(env).encode("utf-8")
        with pytest.raises(ValueError, match="proto version mismatch"):
            decode_envelope(wire)


class TestIsKnownEvent:
    @pytest.mark.parametrize(
        "evt",
        [
            "bounty.posted",
            "team.forming",
            "team.formed",
            "project.submitted",
            "rubric.published",
            "verdict.published",
            "phase.tick",
            "hackathon.closed",
        ],
    )
    def test_known_events(self, evt):
        assert is_known_event(evt) is True

    @pytest.mark.parametrize("evt", ["", "bounty", "bounty.draft", "TEAM.FORMED", "phase.start"])
    def test_unknown_events(self, evt):
        assert is_known_event(evt) is False


class TestPhaseConstants:
    def test_phase_values_are_canonical_order(self):
        assert Phase.BOUNTY_DESIGN == 0
        assert Phase.TEAM_FORMATION == 1
        assert Phase.BUILD == 2
        assert Phase.JUDGING == 3
        assert Phase.SHOWCASE == 4

    def test_all_contains_every_phase(self):
        assert Phase.ALL == (0, 1, 2, 3, 4)


class TestSpecificEnvelopes:
    """Spot-checks for a few real-world envelope shapes from PLAN.md section 5."""

    def test_project_submitted_envelope_carries_commit_hash(self):
        env = make_envelope(
            type="project.submitted",
            round=Phase.BUILD,
            sender_id=VALID_PEER,
            payload={
                "project_id": "proj_2026-04-28_a1",
                "team_id": "team_x",
                "bounty_id": "bnt_3",
                "title": "FoldLens",
                "tagline": "Interactive viewer.",
                "commit_hash": "7f3a2c9",
                "entry_path": "index.html",
                "working_dir": "/tmp/sim/builders/builder_4",
            },
        )
        wire = encode_envelope(env)
        decoded = decode_envelope(wire)
        assert decoded["payload"]["commit_hash"] == "7f3a2c9"
        assert decoded["payload"]["entry_path"] == "index.html"

    def test_phase_tick_envelope(self):
        env = make_envelope(
            type="phase.tick",
            round=Phase.JUDGING,
            sender_id=VALID_PEER,
            payload={"phase": Phase.JUDGING},
        )
        wire = encode_envelope(env)
        decoded = decode_envelope(wire)
        assert decoded["type"] == "phase.tick"
        assert decoded["payload"]["phase"] == Phase.JUDGING

    def test_two_envelopes_different_senders_decode_independently(self):
        a = _make_sample(sender_id=VALID_PEER, payload={"n": 1})
        b = _make_sample(sender_id=ALT_PEER, payload={"n": 2})
        decoded_a = decode_envelope(encode_envelope(a))
        decoded_b = decode_envelope(encode_envelope(b))
        assert decoded_a["sender_id"] != decoded_b["sender_id"]
        assert decoded_a["payload"]["n"] == 1
        assert decoded_b["payload"]["n"] == 2
