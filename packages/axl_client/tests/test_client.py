"""Tests for AxlClient against the FakeAxl stdlib server."""

from __future__ import annotations

import pytest

from packages.axl_client import AxlClient, AxlError, ReceivedMessage
from packages.axl_client.tests._fake_axl import FakeAxl


PEER_A = "a" * 64
PEER_B = "b" * 64
OUR_PEER = "0" * 64


@pytest.fixture
def fake() -> FakeAxl:
    with FakeAxl() as f:
        yield f


@pytest.fixture
def client(fake: FakeAxl) -> AxlClient:
    return AxlClient(fake.url)


class TestConstructor:
    def test_rejects_url_without_scheme(self):
        with pytest.raises(ValueError, match="scheme"):
            AxlClient("127.0.0.1:9002")

    def test_strips_trailing_slash(self):
        c = AxlClient("http://127.0.0.1:9002/")
        assert c.api_url == "http://127.0.0.1:9002"


class TestTopology:
    def test_returns_decoded_topology(self, fake, client):
        fake.state.topology = {
            "our_ipv6": "200::feed",
            "our_public_key": OUR_PEER,
            "peers": [
                {"public_key": PEER_A, "up": True},
                {"public_key": PEER_B, "up": False},
            ],
            "tree": [
                {"public_key": PEER_A},
                {"public_key": "c" * 64},
            ],
        }
        topo = client.get_topology()
        assert topo.our_ipv6 == "200::feed"
        assert topo.our_public_key == OUR_PEER
        assert len(topo.peers) == 2
        assert topo.peers[0].public_key == PEER_A
        assert topo.peers[0].up is True
        assert topo.peers[1].up is False
        assert len(topo.tree) == 2

    def test_handles_missing_optional_fields(self, fake, client):
        fake.state.topology = {"our_public_key": OUR_PEER}
        topo = client.get_topology()
        assert topo.our_public_key == OUR_PEER
        assert topo.peers == []
        assert topo.tree == []

    def test_skips_malformed_peer_entries(self, fake, client):
        fake.state.topology = {
            "our_public_key": OUR_PEER,
            "peers": [
                {"public_key": PEER_A, "up": True},
                "not a dict",
                {"missing": "public_key"},
                {"public_key": PEER_B, "up": True},
            ],
        }
        topo = client.get_topology()
        assert [p.public_key for p in topo.peers] == [PEER_A, PEER_B]

    def test_raises_on_non_200(self, fake, client):
        fake.state.force_status["topology"] = 500
        with pytest.raises(AxlError) as exc:
            client.get_topology()
        assert exc.value.status == 500


class TestSend:
    def test_sends_bytes_with_correct_headers(self, fake, client):
        sent = client.send(PEER_A, b"hello world")
        assert sent == 11
        assert len(fake.state.sent) == 1
        peer, ctype, body = fake.state.sent[0]
        assert peer == PEER_A
        assert ctype == "application/octet-stream"
        assert body == b"hello world"

    def test_send_preserves_custom_content_type(self, fake, client):
        client.send(PEER_A, b'{"k":1}', content_type="application/json")
        _, ctype, _ = fake.state.sent[0]
        assert ctype == "application/json"

    def test_send_accepts_bytearray_and_memoryview(self, fake, client):
        client.send(PEER_A, bytearray(b"abc"))
        client.send(PEER_A, memoryview(b"def"))
        assert [body for _, _, body in fake.state.sent] == [b"abc", b"def"]

    def test_send_rejects_string(self, client):
        with pytest.raises(TypeError):
            client.send(PEER_A, "not bytes")  # type: ignore[arg-type]

    def test_send_raises_on_non_200(self, fake, client):
        fake.state.force_status["send"] = 502
        with pytest.raises(AxlError) as exc:
            client.send(PEER_A, b"x")
        assert exc.value.status == 502


class TestRecv:
    def test_recv_returns_none_on_empty_queue(self, client):
        assert client.recv() is None

    def test_recv_drains_in_order(self, fake, client):
        fake.state.recv_queue.append((PEER_A, b"first"))
        fake.state.recv_queue.append((PEER_B, b"second"))

        m1 = client.recv()
        assert isinstance(m1, ReceivedMessage)
        assert m1.from_peer_id == PEER_A
        assert m1.data == b"first"

        m2 = client.recv()
        assert m2 is not None
        assert m2.from_peer_id == PEER_B
        assert m2.data == b"second"

        assert client.recv() is None

    def test_recv_raises_on_unexpected_status(self, fake, client):
        fake.state.force_status["recv"] = 500
        with pytest.raises(AxlError) as exc:
            client.recv()
        assert exc.value.status == 500


class TestEndToEndShape:
    """A realistic round trip: encode envelope, send via /send, receive via /recv."""

    def test_envelope_round_trips_through_fake(self, fake, client):
        from packages.protocol import Phase, encode_envelope, make_envelope

        env = make_envelope(
            type="bounty.posted",
            round=Phase.BOUNTY_DESIGN,
            sender_id=OUR_PEER,
            payload={"title": "FoldLab", "prize": 2000},
        )
        wire = encode_envelope(env)

        # Sender side: post the envelope.
        sent = client.send(PEER_A, wire, content_type="application/octet-stream")
        assert sent == len(wire)

        # Receiver side: queue it and drain.
        fake.state.recv_queue.append((OUR_PEER, wire))
        msg = client.recv()
        assert msg is not None
        assert msg.from_peer_id == OUR_PEER
        assert msg.data == wire
