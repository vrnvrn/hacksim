"""Tests for SimController.

We use the existing Spawner-injection hooks (keygen, popen, wait_ready) to
boot a fake population without launching real AXL binaries. That lets us
exercise lifecycle, snapshot accumulation, and tailer wiring in
unit-suite time.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from packages.orchestrator import SimConfig, SimController, SseHub
from packages.orchestrator.spawner import Spawner


def _line(event_type: str, payload: dict) -> str:
    return json.dumps({"type": event_type, "payload": payload}) + "\n"


@pytest.fixture
def fake_axl_bin(tmp_path: Path) -> Path:
    bin_path = tmp_path / "axl_bin"
    bin_path.write_text("#!/bin/sh\nsleep 60\n")
    bin_path.chmod(0o755)
    return bin_path


@pytest.fixture
def fake_keygen():
    def keygen(target: Path) -> None:
        target.write_text("-----BEGIN PRIVATE KEY-----\nfake\n-----END PRIVATE KEY-----\n")

    return keygen


@pytest.fixture
def fake_popen():
    """Substitute for subprocess.Popen. Returns a MagicMock that 'runs'."""
    processes: list[MagicMock] = []

    def popen(*args, **kwargs):
        proc = MagicMock()
        proc.pid = 30000 + len(processes)
        proc.poll.return_value = None
        proc.wait.return_value = 0
        proc.terminate = MagicMock()
        proc.kill = MagicMock()
        processes.append(proc)
        return proc

    popen.processes = processes  # type: ignore[attr-defined]
    return popen


@pytest.fixture
def instant_ready():
    def ready(api_url: str, deadline: float) -> None:
        return None

    return ready


@pytest.fixture
def make_controller(tmp_path, fake_axl_bin, fake_keygen, fake_popen, instant_ready):
    """Factory: returns a SimController bound to a fake Spawner."""

    def _make(*, builders: int = 2, judges: int = 1, designers: int = 1) -> SimController:
        hub = SseHub(capacity=128)
        spawner = Spawner(
            base_dir=tmp_path / "sim_x",
            axl_bin=fake_axl_bin,
            sim_id="sim_x",
            keygen=fake_keygen,
            popen=fake_popen,
            wait_ready=instant_ready,
        )
        cfg = SimConfig(builders=builders, judges=judges, designers=designers, pace="smoke")
        return SimController(
            sim_id="sim_x",
            prompt="research hackathon",
            config=cfg,
            hub=hub,
            base_dir=tmp_path / "sim_x",
            axl_bin=fake_axl_bin,
            spawner=spawner,
        )

    return _make


class TestStartLifecycle:
    @pytest.mark.asyncio
    async def test_start_spawns_full_population(self, make_controller):
        controller = make_controller(builders=3, judges=2, designers=2)
        # Skip the topology query since fake nodes have no /topology.
        with patch("packages.orchestrator.controller._query_peer_id", return_value=""):
            await controller.start()
            try:
                assert controller.is_running is True
                assert controller.role_count == 1 + 2 + 3 + 2  # org + designers + builders + judges
            finally:
                await controller.stop()

    @pytest.mark.asyncio
    async def test_start_is_idempotent(self, make_controller):
        controller = make_controller(builders=1, judges=1, designers=1)
        with patch("packages.orchestrator.controller._query_peer_id", return_value=""):
            await controller.start()
            try:
                role_count_after_first_start = controller.role_count
                await controller.start()
                assert controller.role_count == role_count_after_first_start
            finally:
                await controller.stop()

    @pytest.mark.asyncio
    async def test_stop_stops_running(self, make_controller):
        controller = make_controller(builders=1, judges=1, designers=1)
        with patch("packages.orchestrator.controller._query_peer_id", return_value=""):
            await controller.start()
            await controller.stop()
        assert controller.is_running is False


class TestSnapshotEvolution:
    @pytest.mark.asyncio
    async def test_snapshot_starts_empty(self, make_controller):
        controller = make_controller(builders=1, judges=1, designers=1)
        snap = controller.snapshot
        assert snap["bounties"] == []
        assert snap["builders"] == []
        assert snap["projects"] == []
        assert snap["phase"] == 0

    @pytest.mark.asyncio
    async def test_internal_event_folds_into_snapshot(self, make_controller):
        controller = make_controller(builders=1, judges=1, designers=1)
        controller._on_event(  # type: ignore[attr-defined]
            "bounty.posted",
            {"id": "bnt_x", "title": "Demo", "prize_amount_usd": 1000},
        )
        assert len(controller.snapshot["bounties"]) == 1

    @pytest.mark.asyncio
    async def test_publish_writes_to_hub_and_snapshot(self, make_controller):
        controller = make_controller()
        controller._publish("phase.tick", {"phase": 2})  # type: ignore[attr-defined]
        assert controller.snapshot["phase"] == 2
        assert controller.hub.buffer_len("sim_x") == 1


class TestTailerToSnapshot:
    @pytest.mark.asyncio
    async def test_log_lines_flow_to_snapshot(self, make_controller, tmp_path):
        """A tailer attached to a real log file should drive the snapshot."""
        controller = make_controller(builders=1, judges=1, designers=1)

        log_path = tmp_path / "fake_role.worker.log"
        log_path.write_text("")

        # Manually attach a tailer to a known file (bypass the spawner path).
        from packages.orchestrator.log_tailer import LogTailer

        tailer = LogTailer(
            sim_id="sim_x",
            log_path=log_path,
            hub=controller.hub,
            role="bounty_designer",
            listener=controller._on_event,  # type: ignore[arg-type]
            poll_interval=0.05,
        )
        await tailer.start()

        with log_path.open("a") as fp:
            fp.write(_line("bounty.posted", {"id": "bnt_z", "title": "Live"}))
            fp.write(_line("phase.tick", {"phase": 1}))
            fp.flush()

        # Give the tailer a moment to read and fold events.
        for _ in range(20):
            await asyncio.sleep(0.05)
            if (
                len(controller.snapshot["bounties"]) == 1
                and controller.snapshot["phase"] == 1
            ):
                break

        await tailer.stop()
        assert len(controller.snapshot["bounties"]) == 1
        assert controller.snapshot["bounties"][0]["title"] == "Live"
        assert controller.snapshot["phase"] == 1


class TestStartSeedsBuilderRoster:
    @pytest.mark.asyncio
    async def test_builder_registered_events_published(self, make_controller):
        controller = make_controller(builders=2, judges=1, designers=0)
        # Pretend each builder peer id is the api port repeated.
        peer_ids: list[str] = []

        def fake_peer_id(api_url: str) -> str:
            pk = ("a" + str(api_url[-4:])) * 8  # arbitrary 64-ish char hex-ish
            pk = pk[:64].ljust(64, "0")
            peer_ids.append(pk)
            return pk

        with patch(
            "packages.orchestrator.controller._query_peer_id",
            side_effect=fake_peer_id,
        ):
            await controller.start()
            try:
                assert len(controller.snapshot["builders"]) == 2
                for b in controller.snapshot["builders"]:
                    assert b["display_name"].startswith("B-")
                    assert isinstance(b["skills"], list) and len(b["skills"]) > 0
            finally:
                await controller.stop()
