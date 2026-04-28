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
from dataclasses import dataclass, field
from typing import Any, Callable

from packages.axl_client import AxlClient
from packages.protocol import Envelope, decode_envelope
from packages.skills.hacksim_network.hacksim_network import SkillContext


HandlerFn = Callable[["WorkerState", Envelope], None]


@dataclass
class WorkerState:
    """Per-worker mutable state, passed to every handler."""

    ctx: SkillContext
    client: AxlClient
    handlers: dict[str, HandlerFn] = field(default_factory=dict)
    seen: set[tuple[str, str, str]] = field(default_factory=set)
    closed: bool = False

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

    def register(self, envelope_type: str, handler: HandlerFn) -> None:
        self.handlers[envelope_type] = handler


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


def loop_until_closed(state: WorkerState, *, poll_interval: float = 0.5) -> None:
    """Drain /recv, dispatch handlers, sleep, repeat until shutdown.

    Deduplicates by (sender_id, envelope_type, payload_id) so a peer
    that fans out to us via /send and via tree both does not get
    double-handled. The dedupe key matches the autoresearch demo
    (research_network.py:320-374) trimmed to our envelope shape.
    """
    _install_signal_handlers(state)
    state.emit("worker.started", {"api_url": state.client.api_url})

    while not state.closed:
        try:
            msg = state.client.recv()
        except Exception as e:
            state.emit("worker.error", {"phase": "recv", "error": str(e)})
            time.sleep(poll_interval)
            continue

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
            state.emit(
                "envelope.unhandled",
                {"type": env["type"], "from": env["sender_id"][:16]},
            )
            continue

        try:
            handler(state, env)
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
