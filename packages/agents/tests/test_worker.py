"""Tests for the role worker entrypoint.

The worker dispatches by HACKSIM_ROLE. We exercise the unknown-role
branch to make sure a misconfigured spawn surfaces a structured event
rather than silently looking healthy to the orchestrator's log
tailer.
"""

from __future__ import annotations

import json
import threading
import time

import pytest

from packages.agents import worker
from packages.axl_client.tests._fake_axl import FakeAxl
from packages.skills.hacksim_network.hacksim_network import SkillContext


@pytest.fixture
def fake() -> FakeAxl:
    with FakeAxl() as f:
        f.state.topology = {
            "our_ipv6": "200::1",
            "our_public_key": "0" * 64,
            "peers": [],
            "tree": [],
        }
        yield f


def test_unknown_role_emits_structured_event(fake, monkeypatch, capsys):
    """An unknown HACKSIM_ROLE value emits worker.unknown_role on stdout."""
    monkeypatch.setenv("AXL_API_PORT", str(fake._server.server_address[1]))
    monkeypatch.setenv("HACKSIM_ROLE", "garbage_role")
    monkeypatch.setenv("HACKSIM_SIM_ID", "sim_test")

    # stub_heartbeat blocks; run main() in a thread and stop the heartbeat
    # by calling sys.exit-ish via the worker state's closed flag is awkward
    # from outside, so instead we patch stub_heartbeat to a no-op and let
    # main() return immediately after emitting the structured event.
    monkeypatch.setattr(worker, "stub_heartbeat", lambda ctx: None)

    rc = worker.main()
    assert rc == 0

    out = capsys.readouterr().out.splitlines()
    events = [json.loads(line) for line in out]
    unknown = [e for e in events if e["type"] == "worker.unknown_role"]
    assert len(unknown) == 1
    payload = unknown[0]["payload"]
    assert payload["role"] == "garbage_role"
    assert sorted(payload["known_roles"]) == [
        "bounty_designer",
        "builder",
        "judge",
        "organiser",
    ]
    assert unknown[0]["sim_id"] == "sim_test"
    assert unknown[0]["role"] == "garbage_role"


def test_known_role_does_not_emit_unknown_role_event(fake, monkeypatch, capsys):
    """The unknown-role branch does not fire for the four shipping roles."""
    monkeypatch.setenv("AXL_API_PORT", str(fake._server.server_address[1]))
    monkeypatch.setenv("HACKSIM_ROLE", "bounty_designer")
    monkeypatch.setenv("HACKSIM_SIM_ID", "sim_test")

    # Stub the role's run() so the test does not actually launch the loop.
    called = {"n": 0}

    def fake_run(ctx):
        called["n"] += 1

    from packages.agents import bounty_designer

    monkeypatch.setattr(bounty_designer, "run", fake_run, raising=False)

    rc = worker.main()
    assert rc == 0
    assert called["n"] == 1

    out = capsys.readouterr().out
    assert "worker.unknown_role" not in out
