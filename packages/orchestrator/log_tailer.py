"""Tail a role worker's stdout log, publish each JSON line to the hub.

Every spawned role process writes structured events to its
`<work_dir>/<name>.worker.log` file (commit 12). The tailer is a small
async background task per role that reads new lines as they appear,
parses each as JSON, and forwards to the orchestrator's `SseHub`. The
hub fans the event to every subscribed browser; the SimController also
folds the event through `apply_event` to keep the snapshot live.

This module is the bridge between the worker process boundary and the
in-process event bus. It is pure async, no threads, so it composes
with the FastAPI event loop.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable

from .sse import SseHub


# Optional callback invoked for every parsed event. Useful for the
# SimController to fold events through the snapshot accumulator at the
# same time they are published.
ListenerFn = Callable[[str, dict], None]
AsyncListenerFn = Callable[[str, dict], Awaitable[None]]


@dataclass
class LogTailer:
    """One async tailer for one role's worker log."""

    sim_id: str
    log_path: Path
    hub: SseHub
    role: str = ""
    poll_interval: float = 0.2
    listener: ListenerFn | AsyncListenerFn | None = None
    _task: asyncio.Task | None = field(default=None, init=False, repr=False)
    _stop: asyncio.Event | None = field(default=None, init=False, repr=False)
    events_seen: int = field(default=0, init=False)

    async def start(self) -> None:
        """Start the tailer task. Idempotent: re-calls return immediately."""
        if self._task is not None:
            return
        self._stop = asyncio.Event()
        self._task = asyncio.create_task(self._run())

    async def stop(self, *, drain: bool = True) -> None:
        """Signal the tailer to exit. If `drain` is True, read any final
        lines first so the snapshot reflects the worker's last words.
        """
        if self._stop is not None:
            self._stop.set()
        if self._task is None:
            return
        try:
            await asyncio.wait_for(self._task, timeout=2.0)
        except asyncio.TimeoutError:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
        finally:
            self._task = None
            self._stop = None

    async def _run(self) -> None:
        """Async tail loop. Opens the file, follows it, publishes each line."""
        # Wait for the file to appear; the worker creates it on startup.
        wait_deadline = 0
        max_wait_iterations = 200  # ~40s at default poll
        while not self.log_path.exists():
            if self._stop is not None and self._stop.is_set():
                return
            wait_deadline += 1
            if wait_deadline > max_wait_iterations:
                return
            await asyncio.sleep(self.poll_interval)

        leftover = b""
        with self.log_path.open("rb") as fp:
            while True:
                if self._stop is not None and self._stop.is_set():
                    # Drain any remaining bytes once before exiting.
                    chunk = fp.read()
                    if chunk:
                        await self._consume(leftover + chunk)
                    return
                chunk = fp.read()
                if chunk:
                    leftover = await self._consume(leftover + chunk)
                else:
                    await asyncio.sleep(self.poll_interval)

    async def _consume(self, buf: bytes) -> bytes:
        """Split `buf` on newlines, publish complete lines, return any
        unfinished trailer for the next read.
        """
        if b"\n" not in buf:
            return buf
        *lines, trailer = buf.split(b"\n")
        for raw in lines:
            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict):
                continue
            event_type = str(event.get("type", ""))
            payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
            if not event_type:
                continue
            self.events_seen += 1
            await self._publish(event_type, payload)
        return trailer

    async def _publish(self, event_type: str, payload: dict[str, Any]) -> None:
        """Publish the event to the hub and run the listener if any."""
        try:
            self.hub.publish(self.sim_id, event_type, payload)
        except Exception:
            # Hub publish should never raise in normal operation; if it
            # does we still want the tailer to keep going.
            pass
        if self.listener is not None:
            try:
                result = self.listener(event_type, payload)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                pass
