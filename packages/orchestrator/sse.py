"""SSE multiplexer.

Each role process running in a HackSim simulation emits structured events
(envelope JSON plus a small wrapper). The orchestrator collects them and
fans them out to every browser client subscribed to that simulation's
Server-Sent Events stream.

Design:

- One `SseHub` per orchestrator instance.
- `hub.publish(sim_id, event)` is sync and non-blocking. It tags the event
  with a monotonic sequence id, appends to a per-sim ring buffer, and wakes
  every subscriber's queue.
- `hub.subscribe(sim_id, last_event_id=None)` is async. It first replays
  buffered events whose seq is greater than `last_event_id`, then yields
  live events as they arrive. Cancellation cleanly removes the subscriber.

Wire format on the SSE stream is plain SSE: each event is

    id: <seq>\n
    event: <type>\n
    data: <json>\n
    \n

Browsers reconnecting include `Last-Event-ID` so they receive only the
events they missed.
"""

from __future__ import annotations

import asyncio
import json
from collections import deque
from dataclasses import dataclass, field
from typing import AsyncIterator


DEFAULT_CAPACITY = 2000


@dataclass
class Event:
    """One event published to a simulation's stream."""

    seq: int
    type: str
    data: dict
    sim_id: str

    def to_sse_bytes(self) -> bytes:
        """Encode this event as the bytes a browser EventSource consumes."""
        body = (
            f"id: {self.seq}\n"
            f"event: {self.type}\n"
            f"data: {json.dumps(self.data, separators=(',', ':'))}\n\n"
        )
        return body.encode("utf-8")


@dataclass
class _SimChannel:
    """Per-sim state held inside the hub."""

    buffer: deque[Event]
    next_seq: int = 1
    subscribers: set[asyncio.Queue[Event | None]] = field(default_factory=set)
    closed: bool = False


class SseHub:
    """Many-to-many fan-out for simulation events.

    Threadsafe with respect to the asyncio event loop only. The orchestrator
    is single-event-loop; if you call publish() from another thread, marshal
    it via `loop.call_soon_threadsafe`.
    """

    def __init__(self, *, capacity: int = DEFAULT_CAPACITY) -> None:
        if capacity < 1:
            raise ValueError("capacity must be at least 1")
        self.capacity = capacity
        self._channels: dict[str, _SimChannel] = {}

    # ------------------------------------------------------------------ publish

    def publish(self, sim_id: str, event_type: str, data: dict) -> Event:
        """Append one event to a sim's stream and notify every subscriber.

        Returns the Event with its assigned seq, useful for tests and for
        the publisher's own logging. Raises RuntimeError if the channel is
        closed.
        """
        ch = self._channels.get(sim_id)
        if ch is None:
            ch = _SimChannel(buffer=deque(maxlen=self.capacity))
            self._channels[sim_id] = ch
        if ch.closed:
            raise RuntimeError(f"sim {sim_id} channel is closed")
        evt = Event(seq=ch.next_seq, type=event_type, data=data, sim_id=sim_id)
        ch.next_seq += 1
        ch.buffer.append(evt)
        for q in list(ch.subscribers):
            try:
                q.put_nowait(evt)
            except asyncio.QueueFull:
                # Drop on slow consumer rather than blocking the publisher.
                pass
        return evt

    # ---------------------------------------------------------------- subscribe

    async def subscribe(
        self,
        sim_id: str,
        last_event_id: int | None = None,
    ) -> AsyncIterator[Event]:
        """Yield events for a simulation. Replays any buffered events newer
        than `last_event_id` first, then yields live events until cancelled
        or the channel is closed.

        The subscriber is registered in a per-sim set; cancellation triggers
        cleanup in the finally block.
        """
        ch = self._channels.get(sim_id)
        if ch is None:
            ch = _SimChannel(buffer=deque(maxlen=self.capacity))
            self._channels[sim_id] = ch

        # Replay phase: copy the current buffer snapshot so we are not
        # iterating a deque that may be mutated by concurrent publishes.
        snapshot = list(ch.buffer)
        for evt in snapshot:
            if last_event_id is None or evt.seq > last_event_id:
                yield evt
                last_event_id = evt.seq

        if ch.closed:
            return

        # Live phase: register a queue, drain it until cancelled or sentinel.
        q: asyncio.Queue[Event | None] = asyncio.Queue()
        ch.subscribers.add(q)
        try:
            while True:
                evt = await q.get()
                if evt is None:
                    return  # closed sentinel
                if last_event_id is not None and evt.seq <= last_event_id:
                    continue  # already replayed
                yield evt
                last_event_id = evt.seq
        finally:
            ch.subscribers.discard(q)

    # -------------------------------------------------------------------- close

    def close(self, sim_id: str) -> None:
        """Mark a sim's channel closed. Live subscribers will receive a
        None sentinel and exit their async generator."""
        ch = self._channels.get(sim_id)
        if ch is None:
            return
        ch.closed = True
        for q in list(ch.subscribers):
            try:
                q.put_nowait(None)
            except asyncio.QueueFull:
                pass

    # --------------------------------------------------------------- introspection

    def buffer_len(self, sim_id: str) -> int:
        ch = self._channels.get(sim_id)
        return len(ch.buffer) if ch else 0

    def subscriber_count(self, sim_id: str) -> int:
        ch = self._channels.get(sim_id)
        return len(ch.subscribers) if ch else 0

    def has_sim(self, sim_id: str) -> bool:
        return sim_id in self._channels
