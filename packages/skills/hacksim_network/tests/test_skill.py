"""Tests for the hacksim-network skill commands.

Uses the FakeAxl fixture from packages/axl_client/tests/_fake_axl.py to
stand in for a real AXL node, so these tests stay fast and stdlib-only.
"""

from __future__ import annotations

import json

import pytest

from packages.axl_client.tests._fake_axl import FakeAxl
from packages.protocol import Phase, decode_envelope, encode_envelope, make_envelope
from packages.skills.hacksim_network import hacksim_network as skill


PEER_A = "a" * 64
PEER_B = "b" * 64
OUR = "0" * 64


@pytest.fixture
def fake() -> FakeAxl:
    with FakeAxl() as f:
        f.state.topology = {
            "our_ipv6": "200::1",
            "our_public_key": OUR,
            "peers": [{"public_key": PEER_A, "up": True}],
            "tree": [{"public_key": PEER_A}, {"public_key": PEER_B}],
        }
        yield f


@pytest.fixture
def ctx(fake: FakeAxl, monkeypatch) -> skill.SkillContext:
    monkeypatch.setenv("AXL_API_PORT", str(fake._server.server_address[1]))
    monkeypatch.setenv("HACKSIM_ROLE", "designer")
    monkeypatch.setenv("HACKSIM_SIM_ID", "sim_test")
    return skill.SkillContext.from_env()


class TestStatus:
    def test_returns_identity_and_peer_count(self, ctx, fake):
        result = skill.cmd_status(ctx)
        assert result["our_public_key"] == OUR
        assert result["our_ipv6"] == "200::1"
        assert result["peer_count"] == 2  # PEER_A in both, PEER_B in tree only
        assert result["direct_peers"] == 1
        assert result["tree_size"] == 2
        assert result["role"] == "designer"
        assert result["sim_id"] == "sim_test"


class TestRecv:
    def test_returns_empty_when_queue_empty(self, ctx):
        assert skill.cmd_recv(ctx) == []

    def test_decodes_buffered_envelopes(self, ctx, fake):
        env_a = make_envelope(
            type="bounty.posted",
            round=Phase.BOUNTY_DESIGN,
            sender_id=PEER_A,
            payload={"title": "FoldLab"},
        )
        env_b = make_envelope(
            type="phase.tick",
            round=Phase.BUILD,
            sender_id=PEER_B,
            payload={"phase": Phase.BUILD},
        )
        fake.state.recv_queue.append((PEER_A, encode_envelope(env_a)))
        fake.state.recv_queue.append((PEER_B, encode_envelope(env_b)))

        out = skill.cmd_recv(ctx)
        assert len(out) == 2
        assert out[0]["type"] == "bounty.posted"
        assert out[0]["payload"]["title"] == "FoldLab"
        assert out[1]["type"] == "phase.tick"

    def test_skips_non_envelope_messages(self, ctx, fake):
        env = make_envelope(
            type="bounty.posted",
            round=Phase.BOUNTY_DESIGN,
            sender_id=PEER_A,
            payload={"k": "v"},
        )
        fake.state.recv_queue.append((PEER_A, b"not an envelope"))
        fake.state.recv_queue.append((PEER_A, encode_envelope(env)))
        fake.state.recv_queue.append((PEER_A, b'{"some":"json","not":"hacksim"}'))

        out = skill.cmd_recv(ctx)
        assert len(out) == 1
        assert out[0]["type"] == "bounty.posted"


class TestPostBounty:
    def test_designer_can_post(self, ctx, fake):
        result = skill.cmd_post_bounty(
            ctx,
            {
                "title": "FoldLab Privacy Bounty",
                "sponsor_name": "FoldLab",
                "prize_amount_usd": 2000,
                "description": "Best privacy primitive for protein folding.",
            },
        )
        assert result["envelope_type"] == "bounty.posted"
        assert result["round"] == Phase.BOUNTY_DESIGN
        assert result["sent_to"] == 2  # PEER_A and PEER_B reachable

        # Verify the wire shape we sent.
        assert len(fake.state.sent) == 2
        for _peer, ctype, body in fake.state.sent:
            assert ctype == "application/octet-stream"
            env = decode_envelope(body)
            assert env["type"] == "bounty.posted"
            assert env["sender_id"] == OUR
            assert env["payload"]["title"] == "FoldLab Privacy Bounty"
            assert env["payload"]["prize_amount_usd"] == 2000
            assert env["payload"]["qualification"] == []

    def test_builder_cannot_post(self, ctx, monkeypatch):
        monkeypatch.setenv("HACKSIM_ROLE", "builder")
        builder_ctx = skill.SkillContext.from_env()
        with pytest.raises(PermissionError):
            skill.cmd_post_bounty(builder_ctx, {"title": "x"})

    def test_missing_required_field_rejected(self, ctx):
        with pytest.raises(ValueError, match="missing fields"):
            skill.cmd_post_bounty(ctx, {"title": "incomplete"})


class TestSubmitProject:
    def test_builder_can_submit(self, fake, monkeypatch):
        monkeypatch.setenv("AXL_API_PORT", str(fake._server.server_address[1]))
        monkeypatch.setenv("HACKSIM_ROLE", "builder")
        monkeypatch.setenv("HACKSIM_SIM_ID", "sim_test")
        ctx = skill.SkillContext.from_env()

        result = skill.cmd_submit_project(
            ctx,
            {
                "project_id": "proj_x",
                "team_id": "team_x",
                "bounty_id": "bnt_1",
                "title": "FoldLens",
                "tagline": "Interactive viewer.",
                "commit_hash": "7f3a2c9",
                "entry_path": "index.html",
                "working_dir": "/tmp/sim/builders/builder_4",
            },
        )
        assert result["envelope_type"] == "project.submitted"
        assert result["round"] == Phase.BUILD

        decoded = decode_envelope(fake.state.sent[0][2])
        assert decoded["payload"]["project_id"] == "proj_x"
        assert decoded["payload"]["commit_hash"] == "7f3a2c9"

    def test_designer_cannot_submit(self, ctx):
        with pytest.raises(PermissionError):
            skill.cmd_submit_project(
                ctx,
                {
                    "project_id": "p",
                    "team_id": "t",
                    "bounty_id": "b",
                    "title": "x",
                    "tagline": "y",
                    "commit_hash": "h",
                    "entry_path": "i.html",
                    "working_dir": "/tmp/x",
                },
            )

    def test_missing_field_rejected(self, fake, monkeypatch):
        monkeypatch.setenv("AXL_API_PORT", str(fake._server.server_address[1]))
        monkeypatch.setenv("HACKSIM_ROLE", "builder")
        ctx = skill.SkillContext.from_env()
        with pytest.raises(ValueError, match="missing fields"):
            skill.cmd_submit_project(ctx, {"project_id": "p"})


class TestMainCli:
    def test_main_status_writes_json_to_stdout(self, ctx, fake, capsys):
        rc = skill.main(["status"])
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["our_public_key"] == OUR

    def test_main_post_bounty_reads_stdin(self, ctx, fake, capsys, monkeypatch):
        payload = {
            "title": "x",
            "sponsor_name": "y",
            "prize_amount_usd": 100,
            "description": "z",
        }
        import io
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
        rc = skill.main(["post-bounty"])
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["envelope_type"] == "bounty.posted"
        assert out["sent_to"] == 2

    def test_main_returns_1_on_error(self, ctx, fake, capsys, monkeypatch):
        import io
        monkeypatch.setattr("sys.stdin", io.StringIO('{"title": "missing fields"}'))
        rc = skill.main(["post-bounty"])
        assert rc == 1
        captured = capsys.readouterr()
        assert "missing" in captured.err
