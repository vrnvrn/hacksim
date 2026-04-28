"""Integration test: boot two real AXL nodes, exchange one envelope.

The unit ring (commits 04-06) tests AxlClient against a stdlib FakeAxl. This
test promotes the proof to a real Go binary, real Yggdrasil mesh, real TCP
demultiplexer, and the real /recv queue:

- Alice runs an AXL node with Listen=["tls://127.0.0.1:9100"], no upstream peers.
- Bob runs an AXL node with Peers=["tls://127.0.0.1:9100"] and no Listen.
- Bob discovers Alice through the Yggdrasil tree visible at his /topology.
- Bob encodes a HackSim Envelope (bounty.posted) and POSTs it to /send.
- Alice drains it via /recv and decodes it back to the same Envelope.

Skipped when the AXL binary or openssl is missing. Slow (~10s) so it lives
in tests/integration/ and the unit ring stays fast.
"""

from __future__ import annotations

import shutil
import time

import pytest

from packages.axl_client import AxlClient
from packages.protocol import Phase, decode_envelope, encode_envelope, make_envelope

from ._axl_node import axl_binary_available, axl_node


pytestmark = [
    pytest.mark.skipif(not axl_binary_available(), reason="AXL binary not built; run scripts/build_axl.sh"),
    pytest.mark.skipif(shutil.which("openssl") is None, reason="openssl required to generate ed25519 keys"),
]


def _wait_for_peer(client: AxlClient, target_peer_id: str, deadline: float) -> None:
    """Poll `client.all_peer_ids()` until target_peer_id appears or we time out."""
    while time.time() < deadline:
        if target_peer_id in client.all_peer_ids():
            return
        time.sleep(0.5)
    raise TimeoutError(f"peer {target_peer_id[:16]}... not visible in topology")


def _drain_until(client: AxlClient, predicate, deadline: float, log_path=None):
    """Poll /recv until predicate(message) returns True."""
    seen = []
    while time.time() < deadline:
        msg = client.recv()
        if msg is not None:
            seen.append((msg.from_peer_id[:16], msg.data[:60]))
            if predicate(msg):
                return msg
        else:
            time.sleep(0.2)
    detail = f"saw {len(seen)} messages: {seen}"
    if log_path is not None and log_path.exists():
        try:
            tail = log_path.read_text().splitlines()[-30:]
            detail += "\n" + "\n".join(tail)
        except Exception:
            pass
    raise TimeoutError(f"expected message did not arrive on /recv. {detail}")


def test_two_axl_nodes_exchange_one_envelope(tmp_path):
    bootstrap_uri = "tls://127.0.0.1:9100"

    alice_dir = tmp_path / "alice"
    bob_dir = tmp_path / "bob"

    # Both nodes must share the same tcp_port: AXL dials peers via Yggdrasil
    # to <peer_ipv6>:tcp_port, where tcp_port is the LOCAL config value used as
    # the destination port. Different nodes can run on the same machine because
    # the listener lives on the gVisor netstack bound to the Yggdrasil-derived
    # IPv6 address, not on the host stack. See axl/internal/tcp/dial/dial.go.
    with axl_node(
        name="alice",
        work_dir=alice_dir,
        api_port=9202,
        tcp_port=7000,
        listen_uri=bootstrap_uri,
    ) as alice, axl_node(
        name="bob",
        work_dir=bob_dir,
        api_port=9212,
        tcp_port=7000,
        peers=[bootstrap_uri],
    ) as bob:
        alice_client = AxlClient(alice.api_url)
        bob_client = AxlClient(bob.api_url)

        alice_peer = alice_client.get_topology().our_public_key
        bob_peer = bob_client.get_topology().our_public_key
        assert len(alice_peer) == 64
        assert len(bob_peer) == 64
        assert alice_peer != bob_peer

        deadline = time.time() + 30.0
        _wait_for_peer(bob_client, alice_peer, deadline)

        env = make_envelope(
            type="bounty.posted",
            round=Phase.BOUNTY_DESIGN,
            sender_id=bob_peer,
            payload={"bounty_id": "bnt_1", "title": "FoldLab", "prize": 2000},
        )
        wire = encode_envelope(env)
        sent = bob_client.send(alice_peer, wire)
        assert sent == len(wire)

        recv_deadline = time.time() + 15.0
        msg = _drain_until(
            alice_client,
            lambda m: m.data == wire,
            recv_deadline,
            log_path=alice_dir / "alice.log",
        )
        decoded = decode_envelope(msg.data)

        assert decoded["type"] == "bounty.posted"
        assert decoded["round"] == Phase.BOUNTY_DESIGN
        assert decoded["sender_id"] == bob_peer
        assert decoded["payload"]["bounty_id"] == "bnt_1"
        assert decoded["payload"]["title"] == "FoldLab"
        assert decoded["payload"]["prize"] == 2000

        # The X-From-Peer-Id header is derived from the routed Yggdrasil IPv6,
        # which encodes only the first 13 bytes of the public key (the rest is
        # padding). So the header gives us a prefix-equal peer id, not the
        # full key. Authoritative sender identity comes from the envelope's
        # sender_id field, set by the application. See axl/internal/tcp/listen/
        # listener.go:200 (peerIDFromAddr) for the truncation.
        SHARED_PREFIX_HEX = 26  # 13 bytes
        assert msg.from_peer_id.lower()[:SHARED_PREFIX_HEX] == bob_peer.lower()[:SHARED_PREFIX_HEX]
