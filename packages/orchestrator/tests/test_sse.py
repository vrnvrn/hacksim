"""Tests for the SSE multiplexer."""

from __future__ import annotations

import asyncio
import json

import pytest

from packages.orchestrator.sse import Event, SseHub


SIM = "sim_1"
OTHER_SIM = "sim_2"


@pytest.fixture
def hub() -> SseHub:
    return SseHub(capacity=10)


class TestPublish:
    def test_publish_returns_event_with_seq(self, hub):
        e1 = hub.publish(SIM, "bounty.posted", {"id": "b1"})
        e2 = hub.publish(SIM, "bounty.posted", {"id": "b2"})
        assert e1.seq == 1
        assert e2.seq == 2
        assert e1.sim_id == SIM
        assert e1.type == "bounty.posted"

    def test_publish_buffers_events(self, hub):
        for i in range(5):
            hub.publish(SIM, "bounty.posted", {"i": i})
        assert hub.buffer_len(SIM) == 5

    def test_buffer_capacity_drops_oldest(self):
        hub = SseHub(capacity=3)
        for i in range(5):
            hub.publish(SIM, "x", {"i": i})
        assert hub.buffer_len(SIM) == 3

    def test_multiple_sims_have_independent_channels(self, hub):
        hub.publish(SIM, "x", {"a": 1})
        hub.publish(OTHER_SIM, "x", {"a": 1})
        hub.publish(OTHER_SIM, "x", {"a": 2})
        assert hub.buffer_len(SIM) == 1
        assert hub.buffer_len(OTHER_SIM) == 2

    def test_publish_after_close_raises(self, hub):
        hub.publish(SIM, "x", {})
        hub.close(SIM)
        with pytest.raises(RuntimeError, match="closed"):
            hub.publish(SIM, "x", {})


class TestSseEncoding:
    def test_event_to_sse_bytes_format(self):
        e = Event(seq=42, type="bounty.posted", data={"id": "b1"}, sim_id=SIM)
        wire = e.to_sse_bytes()
        decoded = wire.decode("utf-8")
        assert "id: 42" in decoded
        assert "event: bounty.posted" in decoded
        assert "data: " in decoded
        # Body terminates with a blank line.
        assert decoded.endswith("\n\n")

    def test_data_is_compact_json(self):
        e = Event(seq=1, type="x", data={"a": 1, "b": [2, 3]}, sim_id=SIM)
        wire = e.to_sse_bytes().decode("utf-8")
        # Compact: no whitespace inside the JSON.
        data_line = next(line for line in wire.splitlines() if line.startswith("data: "))
        parsed = json.loads(data_line[len("data: "):])
        assert parsed == {"a": 1, "b": [2, 3]}


class TestSubscribeReplay:
    @pytest.mark.asyncio
    async def test_subscribe_with_no_buffer_yields_nothing_until_publish(self, hub):
        async def consume():
            async for evt in hub.subscribe(SIM):
                return evt
            return None

        task = asyncio.create_task(consume())
        await asyncio.sleep(0.01)
        hub.publish(SIM, "x", {"k": "v"})
        result = await asyncio.wait_for(task, timeout=1.0)
        assert result is not None
        assert result.data == {"k": "v"}

    @pytest.mark.asyncio
    async def test_replays_buffered_events(self, hub):
        for i in range(3):
            hub.publish(SIM, "x", {"i": i})

        seen: list[int] = []

        async def consume():
            async for evt in hub.subscribe(SIM):
                seen.append(evt.data["i"])
                if len(seen) == 3:
                    return

        await asyncio.wait_for(consume(), timeout=1.0)
        assert seen == [0, 1, 2]

    @pytest.mark.asyncio
    async def test_replay_skips_events_below_last_event_id(self, hub):
        for i in range(5):
            hub.publish(SIM, "x", {"i": i})

        seen: list[int] = []

        async def consume():
            async for evt in hub.subscribe(SIM, last_event_id=3):
                seen.append(evt.data["i"])
                if len(seen) == 2:
                    return

        await asyncio.wait_for(consume(), timeout=1.0)
        # Buffered events have seq 1..5; last_event_id=3 means we get seq 4 (i=3) and seq 5 (i=4).
        assert seen == [3, 4]


class TestSubscribeLive:
    @pytest.mark.asyncio
    async def test_two_subscribers_each_see_every_event(self, hub):
        seen_a: list[int] = []
        seen_b: list[int] = []

        async def consumer(seen):
            async for evt in hub.subscribe(SIM):
                seen.append(evt.data["i"])
                if len(seen) == 3:
                    return

        a = asyncio.create_task(consumer(seen_a))
        b = asyncio.create_task(consumer(seen_b))
        await asyncio.sleep(0.01)
        for i in range(3):
            hub.publish(SIM, "x", {"i": i})
        await asyncio.gather(a, b, return_exceptions=True)
        assert seen_a == [0, 1, 2]
        assert seen_b == [0, 1, 2]

    @pytest.mark.asyncio
    async def test_subscriber_for_other_sim_does_not_see_events(self, hub):
        seen: list[int] = []

        async def consume():
            try:
                async for evt in hub.subscribe(SIM):
                    seen.append(evt.data["i"])
            except asyncio.CancelledError:
                return

        task = asyncio.create_task(consume())
        await asyncio.sleep(0.01)
        hub.publish(OTHER_SIM, "x", {"i": 99})
        await asyncio.sleep(0.05)
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        assert seen == []

    @pytest.mark.asyncio
    async def test_close_terminates_subscriber(self, hub):
        async def consume():
            count = 0
            async for evt in hub.subscribe(SIM):
                count += 1
            return count

        task = asyncio.create_task(consume())
        await asyncio.sleep(0.01)
        hub.publish(SIM, "x", {"i": 1})
        await asyncio.sleep(0.01)
        hub.close(SIM)
        result = await asyncio.wait_for(task, timeout=1.0)
        assert result == 1


class TestIntrospection:
    def test_subscriber_count_unknown_sim(self, hub):
        assert hub.subscriber_count("never-exists") == 0

    def test_has_sim(self, hub):
        assert hub.has_sim(SIM) is False
        hub.publish(SIM, "x", {})
        assert hub.has_sim(SIM) is True

    def test_invalid_capacity(self):
        with pytest.raises(ValueError):
            SseHub(capacity=0)
