"""Tests for /api/replay/* endpoints.

The replay endpoints read JSONL files written by the Recorder and
expose them as snapshot + SSE-stream pairs that mirror the live
endpoints. The frontend can swap `/api/sim/<id>/...` for
`/api/replay/<id>/...` without other changes.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from packages.orchestrator.api import create_app


def _write_recording(base: Path, run_id: str, *, prompt: str = "demo prompt") -> Path:
    sim_dir = base / run_id
    sim_dir.mkdir(parents=True, exist_ok=True)
    out = sim_dir / "events.jsonl"
    lines: list[dict] = [
        {"meta": {"sim_id": run_id, "prompt": prompt, "started_at": "2026-01-01T00:00:00Z", "config": {"builders": 2, "judges": 1, "designers": 1, "duration_hint": "short", "pace": "quick"}, "schema_version": 1}},
        {"t": 0.0, "type": "sim.created", "data": {"sim_id": run_id, "prompt": prompt, "config": {}}},
        {"t": 0.05, "type": "axl.binary", "data": {"path": "/tmp/axl/node", "size_bytes": 1, "mtime": 0}},
        {"t": 0.10, "type": "phase.tick", "data": {"phase": 1, "phase_name": "BOUNTY_DESIGN"}},
        {"t": 0.20, "type": "phase.tick", "data": {"phase": 5, "phase_name": "SHOWCASE"}},
    ]
    with out.open("w", encoding="utf-8") as fp:
        for line in lines:
            fp.write(json.dumps(line) + "\n")
    return out


@pytest.fixture
def client(tmp_path):
    app = create_app(auto_start=False, base_dir=tmp_path)
    return TestClient(app), tmp_path


class TestReplayList:
    def test_empty_when_no_recordings(self, client):
        c, _ = client
        r = c.get("/api/replay")
        assert r.status_code == 200
        assert r.json() == {"replays": []}

    def test_lists_recordings_with_metadata(self, client):
        c, base = client
        _write_recording(base, "sim_a", prompt="run a")
        _write_recording(base, "sim_b", prompt="run b")
        r = c.get("/api/replay")
        body = r.json()
        ids = sorted(e["run_id"] for e in body["replays"])
        assert ids == ["sim_a", "sim_b"]
        for entry in body["replays"]:
            assert entry["events"] == 4  # four event lines, not counting meta
            assert entry["duration_s"] == 0.2
            assert entry["prompt"] in {"run a", "run b"}

    def test_skips_directories_without_recording(self, client):
        c, base = client
        (base / "sim_partial").mkdir()
        (base / "sim_partial" / "node-keys").mkdir()  # cruft from a half-spawn
        _write_recording(base, "sim_real")
        body = c.get("/api/replay").json()
        ids = [e["run_id"] for e in body["replays"]]
        assert ids == ["sim_real"]


class TestReplaySnapshot:
    def test_returns_404_for_unknown_recording(self, client):
        c, _ = client
        r = c.get("/api/replay/no_such_run/snapshot")
        assert r.status_code == 404

    def test_rejects_path_escape_attempts(self, client):
        c, _ = client
        # Path component containing slashes is rejected by FastAPI's
        # path validation; double dots in the run id are rejected by
        # _replay_path. Hit the latter with a name that the matcher
        # accepts but should not resolve outside base_dir.
        r = c.get("/api/replay/..%2Fevil/snapshot")
        # Either 404 or 400 from path validation; never 200.
        assert r.status_code in (400, 404)

    def test_returns_accumulated_snapshot(self, client):
        c, base = client
        _write_recording(base, "sim_x", prompt="snapshot test")
        r = c.get("/api/replay/sim_x/snapshot")
        assert r.status_code == 200
        body = r.json()
        # Snapshot fields populated by apply_event for these event types.
        assert body["id"] == "sim_x"
        assert body["prompt"] == "snapshot test"
        # phase.tick to phase 5 should have been folded.
        assert body["phase"] == 5


class TestReplayStream:
    def test_streams_events_as_sse(self, client):
        c, base = client
        _write_recording(base, "sim_s")
        # speed=100 to skip the inter-event sleeps.
        with c.stream("GET", "/api/replay/sim_s/stream?speed=100") as r:
            assert r.status_code == 200
            assert r.headers["content-type"].startswith("text/event-stream")
            # Read the first ~2 KB and parse out event types.
            body = b""
            for chunk in r.iter_bytes():
                body += chunk
                if b"replay.finished" in body:
                    break
        text = body.decode("utf-8")
        # `event: <type>` headers per SSE record.
        assert "event: replay.started" in text
        assert "event: sim.created" in text
        assert "event: phase.tick" in text
        assert "event: replay.finished" in text

    def test_unknown_run_returns_404(self, client):
        c, _ = client
        r = c.get("/api/replay/missing/stream")
        assert r.status_code == 404
