"""Tests for AxlClient.all_peer_ids, the peer enumeration logic.

Mirrors the algorithm in research_network.py:214-234 of Gensyn's autoresearch
demo. Each test sets up a topology fixture in the FakeAxl state and asserts on
the deduplicated, self-stripped peer set the client returns.
"""

from __future__ import annotations

import pytest

from packages.axl_client import AxlClient
from packages.axl_client.tests._fake_axl import FakeAxl

OUR = "0" * 64
PEER_A = "a" * 64
PEER_B = "b" * 64
PEER_C = "c" * 64
PEER_D = "d" * 64


@pytest.fixture
def fake() -> FakeAxl:
    with FakeAxl() as f:
        yield f


@pytest.fixture
def client(fake: FakeAxl) -> AxlClient:
    return AxlClient(fake.url)


def test_empty_mesh_returns_empty_list(fake, client):
    fake.state.topology = {
        "our_public_key": OUR,
        "peers": [],
        "tree": [],
    }
    assert client.all_peer_ids() == []


def test_only_direct_peers(fake, client):
    fake.state.topology = {
        "our_public_key": OUR,
        "peers": [
            {"public_key": PEER_A, "up": True},
            {"public_key": PEER_B, "up": True},
        ],
        "tree": [],
    }
    assert sorted(client.all_peer_ids()) == sorted([PEER_A, PEER_B])


def test_only_tree_entries(fake, client):
    fake.state.topology = {
        "our_public_key": OUR,
        "peers": [],
        "tree": [
            {"public_key": PEER_C},
            {"public_key": PEER_D},
        ],
    }
    assert sorted(client.all_peer_ids()) == sorted([PEER_C, PEER_D])


def test_unioned_dedup(fake, client):
    """A peer in both direct list and tree appears once."""
    fake.state.topology = {
        "our_public_key": OUR,
        "peers": [
            {"public_key": PEER_A, "up": True},
            {"public_key": PEER_B, "up": True},
        ],
        "tree": [
            {"public_key": PEER_A},
            {"public_key": PEER_C},
        ],
    }
    assert sorted(client.all_peer_ids()) == sorted([PEER_A, PEER_B, PEER_C])


def test_skips_down_direct_peers(fake, client):
    fake.state.topology = {
        "our_public_key": OUR,
        "peers": [
            {"public_key": PEER_A, "up": True},
            {"public_key": PEER_B, "up": False},
        ],
        "tree": [],
    }
    assert client.all_peer_ids() == [PEER_A]


def test_down_peer_recovered_from_tree(fake, client):
    """Tree entries do not have an `up` field; everything in the tree counts."""
    fake.state.topology = {
        "our_public_key": OUR,
        "peers": [
            {"public_key": PEER_B, "up": False},
        ],
        "tree": [
            {"public_key": PEER_B},
            {"public_key": PEER_C},
        ],
    }
    assert sorted(client.all_peer_ids()) == sorted([PEER_B, PEER_C])


def test_self_is_discarded(fake, client):
    fake.state.topology = {
        "our_public_key": OUR,
        "peers": [
            {"public_key": OUR, "up": True},
            {"public_key": PEER_A, "up": True},
        ],
        "tree": [
            {"public_key": OUR},
            {"public_key": PEER_B},
        ],
    }
    result = client.all_peer_ids()
    assert OUR not in result
    assert sorted(result) == sorted([PEER_A, PEER_B])


def test_returns_list_not_set(fake, client):
    """The return type matters: callers iterate, sort, and broadcast."""
    fake.state.topology = {
        "our_public_key": OUR,
        "peers": [{"public_key": PEER_A, "up": True}],
        "tree": [{"public_key": PEER_B}],
    }
    result = client.all_peer_ids()
    assert isinstance(result, list)


def test_handles_missing_optional_topology_fields(fake, client):
    fake.state.topology = {"our_public_key": OUR}
    assert client.all_peer_ids() == []


def test_realistic_mesh_dedup(fake, client):
    """Realistic mesh: us, two direct peers, four tree entries, one overlap."""
    fake.state.topology = {
        "our_ipv6": "200::1",
        "our_public_key": OUR,
        "peers": [
            {"public_key": PEER_A, "up": True},
            {"public_key": PEER_B, "up": True},
        ],
        "tree": [
            {"public_key": PEER_A},      # overlap with direct
            {"public_key": PEER_C},
            {"public_key": PEER_D},
            {"public_key": OUR},         # self, must drop
        ],
    }
    assert sorted(client.all_peer_ids()) == sorted([PEER_A, PEER_B, PEER_C, PEER_D])
