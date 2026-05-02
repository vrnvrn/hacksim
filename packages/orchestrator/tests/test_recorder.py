"""Tests for the JSONL recorder.

The recorder mirrors every hub.publish into a per-sim file under
sim-runs/<sim_id>/events.jsonl. The replay route reads those files;
those tests live in test_api.py.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from packages.orchestrator.recorder import Recorder, read_recording


@pytest.fixture
def recording_path(tmp_path: Path) -> Path:
    return tmp_path / "events.jsonl"


def test_open_writes_meta_record(recording_path):
    rec = Recorder(path=recording_path)
    rec.open(meta={"sim_id": "sim_test", "prompt": "test prompt", "started_at": "2026-01-01T00:00:00Z", "config": {"builders": 2}})
    rec.close()

    lines = recording_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    obj = json.loads(lines[0])
    assert obj["meta"]["sim_id"] == "sim_test"
    assert obj["meta"]["schema_version"] == 1
    assert obj["meta"]["config"] == {"builders": 2}


def test_record_appends_events_with_monotonic_t(recording_path):
    rec = Recorder(path=recording_path)
    rec.open(meta={"sim_id": "s1", "prompt": "p", "started_at": "now", "config": {}})
    rec.record("phase.tick", {"phase": 1})
    rec.record("phase.tick", {"phase": 2})
    rec.close()

    meta, events = read_recording(recording_path)
    assert meta["sim_id"] == "s1"
    assert len(events) == 2
    assert events[0]["type"] == "phase.tick"
    assert events[0]["data"] == {"phase": 1}
    assert events[1]["t"] >= events[0]["t"]


def test_record_after_close_is_noop(recording_path):
    rec = Recorder(path=recording_path)
    rec.open(meta={"sim_id": "s2", "prompt": "p", "started_at": "now", "config": {}})
    rec.record("a", {})
    rec.close()
    rec.record("b", {})  # must not raise, must not write
    _, events = read_recording(recording_path)
    assert [e["type"] for e in events] == ["a"]


def test_close_is_idempotent(recording_path):
    rec = Recorder(path=recording_path)
    rec.open(meta={"sim_id": "s3", "prompt": "p", "started_at": "now", "config": {}})
    rec.close()
    rec.close()


def test_read_recording_missing_meta_raises(tmp_path):
    p = tmp_path / "bad.jsonl"
    p.write_text(
        '{"t": 0.0, "type": "phase.tick", "data": {}}\n', encoding="utf-8"
    )
    with pytest.raises(ValueError, match="missing meta record"):
        read_recording(p)


def test_read_recording_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_recording(tmp_path / "nope.jsonl")


def test_read_recording_skips_garbage_lines(tmp_path):
    p = tmp_path / "ok.jsonl"
    p.write_text(
        '{"meta": {"sim_id": "s", "schema_version": 1}}\n'
        "this is not json\n"
        "\n"
        '{"t": 0.1, "type": "a", "data": {}}\n'
        '{"t": 0.2, "missing": "type"}\n'
        '{"t": 0.3, "type": "b", "data": {}}\n',
        encoding="utf-8",
    )
    meta, events = read_recording(p)
    assert meta["sim_id"] == "s"
    assert [e["type"] for e in events] == ["a", "b"]


class TestHubIntegration:
    """The recorder is wired to SseHub via add_publish_listener."""

    def test_listener_receives_every_published_event(self, tmp_path):
        from packages.orchestrator.sse import SseHub

        hub = SseHub()
        rec = Recorder(path=tmp_path / "events.jsonl")
        rec.open(meta={"sim_id": "sim_x", "prompt": "p", "started_at": "now", "config": {}})

        def on_publish(evt):
            rec.record(evt.type, evt.data)

        hub.add_publish_listener("sim_x", on_publish)
        hub.publish("sim_x", "phase.tick", {"phase": 1})
        hub.publish("sim_x", "phase.tick", {"phase": 2})
        hub.remove_publish_listener("sim_x", on_publish)
        hub.publish("sim_x", "phase.tick", {"phase": 3})  # must not be recorded
        rec.close()

        _, events = read_recording(tmp_path / "events.jsonl")
        phases = [e["data"]["phase"] for e in events]
        assert phases == [1, 2]

    def test_listener_failure_does_not_break_publish(self):
        from packages.orchestrator.sse import SseHub

        hub = SseHub()

        def boom(evt):
            raise RuntimeError("listener bug")

        hub.add_publish_listener("sim_y", boom)
        # Publishing must still return a valid event.
        evt = hub.publish("sim_y", "test", {"k": "v"})
        assert evt.seq == 1
