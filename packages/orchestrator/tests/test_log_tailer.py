"""Tests for the worker log tailer."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from packages.orchestrator import SseHub
from packages.orchestrator.log_tailer import LogTailer


def _line(event_type: str, payload: dict) -> str:
    return json.dumps({"type": event_type, "payload": payload}) + "\n"


@pytest.mark.asyncio
async def test_tailer_publishes_each_existing_line(tmp_path):
    log = tmp_path / "worker.log"
    log.write_text(_line("bounty.posted", {"id": "bnt_1"}) + _line("phase.tick", {"phase": 2}))
    hub = SseHub(capacity=64)
    tailer = LogTailer(sim_id="sim_a", log_path=log, hub=hub, poll_interval=0.05)
    await tailer.start()
    await asyncio.sleep(0.4)
    await tailer.stop()
    assert hub.buffer_len("sim_a") == 2


@pytest.mark.asyncio
async def test_tailer_picks_up_lines_appended_after_start(tmp_path):
    log = tmp_path / "worker.log"
    log.write_text("")  # exists, empty
    hub = SseHub(capacity=64)
    tailer = LogTailer(sim_id="sim_a", log_path=log, hub=hub, poll_interval=0.05)
    await tailer.start()
    await asyncio.sleep(0.1)
    with log.open("a") as fp:
        fp.write(_line("bounty.posted", {"id": "x"}))
        fp.write(_line("project.submitted", {"project_id": "p"}))
        fp.flush()
    await asyncio.sleep(0.4)
    await tailer.stop()
    assert hub.buffer_len("sim_a") == 2


@pytest.mark.asyncio
async def test_tailer_handles_partial_line_across_reads(tmp_path):
    log = tmp_path / "worker.log"
    log.write_text("")
    hub = SseHub(capacity=64)
    tailer = LogTailer(sim_id="sim_a", log_path=log, hub=hub, poll_interval=0.05)
    await tailer.start()
    await asyncio.sleep(0.05)
    with log.open("a") as fp:
        fp.write('{"type":"bounty.posted","payload":{"id"')
        fp.flush()
    await asyncio.sleep(0.2)
    assert hub.buffer_len("sim_a") == 0  # not yet a complete line
    with log.open("a") as fp:
        fp.write(':"x"}}\n')
        fp.flush()
    await asyncio.sleep(0.3)
    await tailer.stop()
    assert hub.buffer_len("sim_a") == 1


@pytest.mark.asyncio
async def test_tailer_skips_malformed_json(tmp_path):
    log = tmp_path / "worker.log"
    log.write_text(
        "not json\n"
        + _line("bounty.posted", {"id": "x"})
        + "{\"type\":\"missing-payload\"}\n"  # valid JSON but no 'payload' key, payload defaults
        + _line("phase.tick", {"phase": 1})
    )
    hub = SseHub(capacity=64)
    tailer = LogTailer(sim_id="sim_a", log_path=log, hub=hub, poll_interval=0.05)
    await tailer.start()
    await asyncio.sleep(0.4)
    await tailer.stop()
    # The malformed JSON line is dropped, the missing-payload line still publishes
    # with payload={}, so buffer holds 3 events.
    assert hub.buffer_len("sim_a") == 3


@pytest.mark.asyncio
async def test_tailer_calls_listener_per_event(tmp_path):
    log = tmp_path / "worker.log"
    log.write_text(_line("bounty.posted", {"id": "x"}))
    hub = SseHub(capacity=64)
    seen: list[tuple[str, dict]] = []

    def listener(event_type: str, payload: dict) -> None:
        seen.append((event_type, payload))

    tailer = LogTailer(
        sim_id="sim_a",
        log_path=log,
        hub=hub,
        poll_interval=0.05,
        listener=listener,
    )
    await tailer.start()
    await asyncio.sleep(0.3)
    await tailer.stop()
    assert seen == [("bounty.posted", {"id": "x"})]


@pytest.mark.asyncio
async def test_async_listener_awaited(tmp_path):
    log = tmp_path / "worker.log"
    log.write_text(_line("bounty.posted", {"id": "x"}))
    hub = SseHub(capacity=64)
    seen: list[str] = []

    async def listener(event_type: str, payload: dict) -> None:
        await asyncio.sleep(0)  # confirm it is awaited
        seen.append(event_type)

    tailer = LogTailer(
        sim_id="sim_a",
        log_path=log,
        hub=hub,
        poll_interval=0.05,
        listener=listener,
    )
    await tailer.start()
    await asyncio.sleep(0.3)
    await tailer.stop()
    assert seen == ["bounty.posted"]


@pytest.mark.asyncio
async def test_tailer_waits_for_file_to_appear(tmp_path):
    log = tmp_path / "worker.log"  # does not exist yet
    hub = SseHub(capacity=64)
    tailer = LogTailer(sim_id="sim_a", log_path=log, hub=hub, poll_interval=0.05)
    await tailer.start()
    await asyncio.sleep(0.1)
    log.write_text(_line("bounty.posted", {"id": "x"}))
    await asyncio.sleep(0.3)
    await tailer.stop()
    assert hub.buffer_len("sim_a") == 1


@pytest.mark.asyncio
async def test_stop_drains_remaining(tmp_path):
    log = tmp_path / "worker.log"
    log.write_text(_line("bounty.posted", {"id": "x"}))
    hub = SseHub(capacity=64)
    tailer = LogTailer(sim_id="sim_a", log_path=log, hub=hub, poll_interval=0.5)
    await tailer.start()
    # Append before the tailer's next poll, then stop.
    with log.open("a") as fp:
        fp.write(_line("phase.tick", {"phase": 1}))
        fp.flush()
    await asyncio.sleep(0.05)  # too short for next poll
    await tailer.stop(drain=True)
    # Both events should have been published.
    assert hub.buffer_len("sim_a") == 2
