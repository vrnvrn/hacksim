"""Tests for the role worker runtime.

The runtime is the shared loop: drain /recv, dispatch handlers, dedupe,
emit heartbeats. We test it against a FakeAxl so we exercise the real
AxlClient without spawning a real node.
"""

from __future__ import annotations

import json
import threading

import pytest

from packages.axl_client.tests._fake_axl import FakeAxl
from packages.protocol import Phase, encode_envelope, make_envelope
from packages.skills.hacksim_network.hacksim_network import SkillContext

from packages.agents._runtime import WorkerState, loop_until_closed


PEER_A = "a" * 64
PEER_B = "b" * 64
OUR = "0" * 64


@pytest.fixture
def fake() -> FakeAxl:
    with FakeAxl() as f:
        f.state.topology = {
            "our_ipv6": "200::1",
            "our_public_key": OUR,
            "peers": [],
            "tree": [],
        }
        yield f


@pytest.fixture
def ctx(fake: FakeAxl, monkeypatch) -> SkillContext:
    monkeypatch.setenv("AXL_API_PORT", str(fake._server.server_address[1]))
    monkeypatch.setenv("HACKSIM_ROLE", "stub")
    monkeypatch.setenv("HACKSIM_SIM_ID", "sim_test")
    return SkillContext.from_env()


def _run_loop_briefly(state: WorkerState, duration_s: float = 0.4):
    """Run loop_until_closed in a thread; ask it to stop after `duration_s`."""

    def runner():
        loop_until_closed(state, poll_interval=0.05)

    t = threading.Thread(target=runner, daemon=True)
    t.start()
    import time
    time.sleep(duration_s)
    state.closed = True
    t.join(timeout=2.0)
    assert not t.is_alive(), "worker thread did not exit"


class TestEmit:
    def test_emit_writes_json_line_to_stdout(self, ctx, capsys):
        state = WorkerState(ctx=ctx, client=ctx.client())
        state.emit("test", {"k": "v"})
        out = capsys.readouterr().out.strip()
        parsed = json.loads(out)
        assert parsed["type"] == "test"
        assert parsed["payload"] == {"k": "v"}
        assert parsed["role"] == "stub"
        assert parsed["sim_id"] == "sim_test"


class TestLoopHandlers:
    def test_handler_receives_envelope(self, ctx, fake, capsys):
        state = WorkerState(ctx=ctx, client=ctx.client())

        seen: list[dict] = []

        def on_bounty(s, env):
            seen.append(dict(env["payload"]))

        state.register("bounty.posted", on_bounty)

        env = make_envelope(
            type="bounty.posted",
            round=Phase.BOUNTY_DESIGN,
            sender_id=PEER_A,
            payload={"id": "b1", "title": "FoldLab"},
        )
        fake.state.recv_queue.append((PEER_A, encode_envelope(env)))

        _run_loop_briefly(state)

        assert seen == [{"id": "b1", "title": "FoldLab"}]

    def test_unhandled_envelope_logged(self, ctx, fake, capsys):
        state = WorkerState(ctx=ctx, client=ctx.client())

        env = make_envelope(
            type="phase.tick",
            round=Phase.BUILD,
            sender_id=PEER_A,
            payload={"phase": Phase.BUILD},
        )
        fake.state.recv_queue.append((PEER_A, encode_envelope(env)))

        _run_loop_briefly(state)

        out = capsys.readouterr().out.splitlines()
        unhandled = [json.loads(line) for line in out if "envelope.unhandled" in line]
        assert len(unhandled) == 1
        assert unhandled[0]["payload"]["type"] == "phase.tick"

    def test_dedupe_drops_repeat(self, ctx, fake, capsys):
        state = WorkerState(ctx=ctx, client=ctx.client())

        seen_count = {"n": 0}

        def on_bounty(s, env):
            seen_count["n"] += 1

        state.register("bounty.posted", on_bounty)

        env = make_envelope(
            type="bounty.posted",
            round=Phase.BOUNTY_DESIGN,
            sender_id=PEER_A,
            payload={"id": "b1"},
        )
        wire = encode_envelope(env)
        fake.state.recv_queue.append((PEER_A, wire))
        fake.state.recv_queue.append((PEER_A, wire))
        fake.state.recv_queue.append((PEER_A, wire))

        _run_loop_briefly(state)

        assert seen_count["n"] == 1

    def test_handler_exception_does_not_kill_loop(self, ctx, fake, capsys):
        state = WorkerState(ctx=ctx, client=ctx.client())

        def boom(s, env):
            raise RuntimeError("oops")

        state.register("bounty.posted", boom)

        env_a = make_envelope(
            type="bounty.posted",
            round=Phase.BOUNTY_DESIGN,
            sender_id=PEER_A,
            payload={"id": "b1"},
        )
        env_b = make_envelope(
            type="bounty.posted",
            round=Phase.BOUNTY_DESIGN,
            sender_id=PEER_B,
            payload={"id": "b2"},
        )
        fake.state.recv_queue.append((PEER_A, encode_envelope(env_a)))
        fake.state.recv_queue.append((PEER_B, encode_envelope(env_b)))

        _run_loop_briefly(state)

        out = capsys.readouterr().out.splitlines()
        errors = [json.loads(line) for line in out if "handler_error" in line]
        assert len(errors) == 2  # both handler invocations errored, loop survived

    def test_non_envelope_message_skipped(self, ctx, fake, capsys):
        state = WorkerState(ctx=ctx, client=ctx.client())
        fake.state.recv_queue.append((PEER_A, b"not json envelope"))

        _run_loop_briefly(state)

        out = capsys.readouterr().out.splitlines()
        skipped = [json.loads(line) for line in out if "worker.skipped" in line]
        assert len(skipped) == 1


class TestBroadcastNow:
    def test_send_failures_are_rolled_up_into_one_event(self, ctx, fake, capsys):
        """All per-peer failures across one fanout become one event.

        Payload carries `failure_count`, `success_count`, and a
        `failures: [...]` array. One log line per fanout, not one per
        peer per retry.
        """
        client = ctx.client()
        boom = RuntimeError("simulated send failure")

        def failing_send(peer_id: str, data: bytes, **_: object) -> int:
            raise boom

        client.send = failing_send  # type: ignore[method-assign]
        fake.state.topology = {
            "our_ipv6": "200::1",
            "our_public_key": OUR,
            "peers": [{"public_key": PEER_A, "up": True}],
            "tree": [{"public_key": PEER_B}],
        }

        state = WorkerState(ctx=ctx, client=client)
        sent = state.broadcast_now(b"payload")
        assert sent == 0

        out = capsys.readouterr().out.splitlines()
        events = [json.loads(line) for line in out if "axl.send_failed" in line]
        assert len(events) == 1
        payload = events[0]["payload"]
        assert payload["failure_count"] == 2
        assert payload["success_count"] == 0
        peer_ids = sorted(f["peer_id"] for f in payload["failures"])
        assert peer_ids == sorted([PEER_A, PEER_B])
        for f in payload["failures"]:
            assert f["error_class"] == "RuntimeError"
            assert "simulated send failure" in f["error"]

    def test_no_event_when_every_peer_succeeds(self, ctx, fake, capsys):
        """Successful fanouts emit no axl.send_failed event at all."""
        fake.state.topology = {
            "our_ipv6": "200::1",
            "our_public_key": OUR,
            "peers": [{"public_key": PEER_A, "up": True}],
            "tree": [],
        }
        state = WorkerState(ctx=ctx, client=ctx.client())
        sent = state.broadcast_now(b"payload")
        assert sent == 1
        out = capsys.readouterr().out
        assert "axl.send_failed" not in out


class TestStartStopEvents:
    def test_started_and_stopped_events_emitted(self, ctx, fake, capsys):
        state = WorkerState(ctx=ctx, client=ctx.client())
        _run_loop_briefly(state)
        out = capsys.readouterr().out.splitlines()
        types = [json.loads(line)["type"] for line in out]
        assert types[0] == "worker.started"
        assert types[-1] == "worker.stopped"
