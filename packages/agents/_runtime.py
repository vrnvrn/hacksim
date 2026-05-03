"""Shared runtime for HackSim role workers.

Owns the heartbeat loop, the signal-driven shutdown, and the structured
event emission to stdout (so the orchestrator can multiplex them into
SSE).

Each role's `run(ctx)` builds on top of this: it registers handlers for
the envelope types it cares about, then `loop_until_closed` runs the
event loop.
"""

from __future__ import annotations

import json
import signal
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from packages.axl_client import AxlClient
from packages.protocol import Envelope, decode_envelope, is_known_event
from packages.skills.hacksim_network.hacksim_network import SkillContext

HandlerFn = Callable[["WorkerState", Envelope], None]


@dataclass
class WorkerState:
    """Per-worker mutable state, passed to every handler."""

    ctx: SkillContext
    client: AxlClient
    handlers: dict[str, HandlerFn] = field(default_factory=dict)
    gossip_types: set[str] = field(default_factory=set)
    seen: set[tuple[str, str, str]] = field(default_factory=set)
    closed: bool = False
    timers: list[tuple[float, Callable[[WorkerState], None]]] = field(default_factory=list)

    def emit(self, event_type: str, payload: dict[str, Any]) -> None:
        """Write one structured event line to stdout. The orchestrator's
        log reader parses these JSON lines and forwards them to the SSE hub.
        """
        line = json.dumps(
            {
                "ts": time.time(),
                "role": self.ctx.role,
                "sim_id": self.ctx.sim_id,
                "type": event_type,
                "payload": payload,
            },
            separators=(",", ":"),
        )
        sys.stdout.write(line + "\n")
        sys.stdout.flush()

    def register(
        self,
        envelope_type: str,
        handler: HandlerFn,
        *,
        gossip: bool = False,
    ) -> None:
        """Register a handler for one envelope type.

        When `gossip=True`, the runtime re-fanouts the original wire bytes
        after the handler returns, exactly once per (sender, type, payload_id)
        pair (dedupe is the same set used for handler dispatch). Together
        with the deferred re-broadcast scheduled at broadcast time, this
        gives the mesh epidemic-style propagation that catches peers whose
        Yggdrasil tree had not propagated when the original sender fanned
        out. Gossip terminates because every receiver dedupes on arrival.
        """
        self.handlers[envelope_type] = handler
        if gossip:
            self.gossip_types.add(envelope_type)

    def schedule(self, fn: Callable[[WorkerState], None], delay: float) -> None:
        """Run `fn(state)` once after `delay` seconds.

        The main loop processes due timers each tick. Multiple timers fire
        in registration order if they are due at the same tick.
        """
        self.timers.append((time.time() + delay, fn))

    def broadcast_now(self, wire: bytes) -> int:
        """Fan-out `wire` to every peer in topology. Returns success count.

        Per-peer send failures are collected across the fanout and
        emitted as one `axl.send_failed` event with a `failures: [...]`
        array. One log line per fanout, not one per peer per retry, so a
        misconfigured mesh does not drown the run log under 28 identical
        lines per envelope (default population is 14 peers and fanout
        retries twice).
        """
        sent = 0
        failures: list[dict[str, str]] = []
        for peer_id in self.client.all_peer_ids():
            try:
                self.client.send(peer_id, wire)
                sent += 1
            except Exception as exc:
                failures.append(
                    {
                        "peer_id": peer_id,
                        "error_class": type(exc).__name__,
                        "error": str(exc),
                    }
                )
        if failures:
            self.emit(
                "axl.send_failed",
                {
                    "failure_count": len(failures),
                    "success_count": sent,
                    "failures": failures,
                },
            )
        return sent

    def fanout(
        self,
        wire: bytes,
        *,
        repeats: int = 2,
        interval: float = 2.5,
    ) -> int:
        """Broadcast `wire` now plus schedule `repeats` re-broadcasts at
        `interval` seconds apart.

        The re-broadcasts catch peers whose Yggdrasil spanning-tree view
        had not propagated when the first broadcast went out. This is the
        same retry pattern Gensyn's autoresearch demo uses (re-share each
        finding once per cycle).
        """
        sent = self.broadcast_now(wire)
        for i in range(1, repeats + 1):
            delay = interval * i
            self.schedule(lambda s, w=wire: s.broadcast_now(w), delay)
        return sent


def _install_signal_handlers(state: WorkerState) -> None:
    """Install SIGINT and SIGTERM handlers if we are in the main thread.

    Python disallows signal installation from worker threads. The loop is
    designed to be runnable from either context (real role processes call
    it from the main thread; tests run it from a worker thread). When we
    are off the main thread we skip signal installation; tests stop the
    loop by setting `state.closed = True` directly.
    """
    import threading

    if threading.current_thread() is not threading.main_thread():
        return

    def _stop(_signum, _frame):
        state.closed = True

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)


RECV_FATAL_AFTER = 20
RECV_BACKOFF_MAX = 16.0


def loop_until_closed(state: WorkerState, *, poll_interval: float = 0.5) -> None:
    """Drain /recv, dispatch handlers, run due timers, sleep, repeat.

    Deduplicates by (sender_id, envelope_type, payload_id) so a peer
    that fans out to us via /send and via tree both does not get
    double-handled. The dedupe key matches the autoresearch demo
    (research_network.py:320-374) trimmed to our envelope shape.

    Recv() failures use exponential backoff capped at `RECV_BACKOFF_MAX`
    seconds. After `RECV_FATAL_AFTER` consecutive failures the loop
    emits `worker.fatal` and exits. A dead AXL node used to spam
    `worker.error` twice per second forever, drowning the run log
    without surfacing the actual problem; the breaker turns that into
    one fatal event the SSE consumer can act on.
    """
    _install_signal_handlers(state)
    state.emit("worker.started", {"api_url": state.client.api_url})

    recv_failures = 0
    recv_backoff = poll_interval

    while not state.closed:
        # Fire any due timers first so re-broadcasts go out promptly.
        now = time.time()
        due: list[tuple[float, Callable[[WorkerState], None]]] = [
            t for t in state.timers if t[0] <= now
        ]
        for t in due:
            try:
                state.timers.remove(t)
            except ValueError:
                pass
            try:
                t[1](state)
            except Exception as e:
                state.emit("worker.timer_error", {"error": str(e)})

        try:
            msg = state.client.recv()
        except Exception as e:
            recv_failures += 1
            state.emit(
                "worker.error",
                {
                    "phase": "recv",
                    "error": str(e),
                    "consecutive_failures": recv_failures,
                },
            )
            if recv_failures >= RECV_FATAL_AFTER:
                state.emit(
                    "worker.fatal",
                    {
                        "phase": "recv",
                        "consecutive_failures": recv_failures,
                        "last_error": str(e),
                    },
                )
                break
            time.sleep(recv_backoff)
            recv_backoff = min(recv_backoff * 2, RECV_BACKOFF_MAX)
            continue

        recv_failures = 0
        recv_backoff = poll_interval

        if msg is None:
            time.sleep(poll_interval)
            continue

        try:
            env = decode_envelope(msg.data)
        except ValueError:
            state.emit("worker.skipped", {"reason": "non-envelope"})
            continue

        payload_id = str(env["payload"].get("id") or env["payload"].get("project_id") or env["timestamp"])
        key = (env["sender_id"], env["type"], payload_id)
        if key in state.seen:
            continue
        state.seen.add(key)

        handler = state.handlers.get(env["type"])
        if handler is None:
            # Silently drop envelopes the protocol declares but this role
            # did not register a handler for (typical case: a builder
            # receiving verdict.published from a judge, or a designer
            # receiving team.formed from a builder). Every envelope is
            # broadcast to every peer in the mesh; without this guard the
            # run log fills with ~100 cosmetic envelope.unhandled entries
            # per sim. Only emit the diagnostic when the type is genuinely
            # unknown to the protocol, which is the case the run log is
            # supposed to surface (a misconfigured spawn, a stale build,
            # protocol drift between roles).
            if not is_known_event(env["type"]):
                state.emit(
                    "envelope.unhandled",
                    {"type": env["type"], "from": env["sender_id"][:16]},
                )
            continue

        try:
            handler(state, env)
            if env["type"] in state.gossip_types:
                # Re-forward the original wire bytes so peers our sender
                # could not reach (yet) get a chance to receive it.
                try:
                    state.broadcast_now(msg.data)
                except Exception as e:
                    state.emit("worker.gossip_error", {"error": str(e)})
        except Exception as e:
            state.emit(
                "worker.handler_error",
                {"type": env["type"], "error": str(e)},
            )

    state.emit("worker.stopped", {})


def stub_heartbeat(ctx: SkillContext) -> None:
    """Default 'role with no behaviour yet' loop. Used for any unknown
    role and for the harness test in commit 12. Just drains envelopes
    and emits heartbeats.
    """
    state = WorkerState(ctx=ctx, client=ctx.client())
    loop_until_closed(state)
