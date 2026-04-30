"""Integration test: removing AXL stops the simulation immediately.

The README claims "removing AXL silences the simulation." This test
proves it the cheap way: SimController.start with an invalid axl_bin
must raise quickly with a clear error, not hang or fall back to a
mock transport.

The test is small and fast enough to run alongside the unit ring; we
keep it in tests/integration/ because it documents an end-to-end
contract about the demo's dependency on the AXL Go binary.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from packages.orchestrator import SpawnerError
from packages.orchestrator.controller import SimConfig, SimController
from packages.orchestrator.sse import SseHub


def test_sim_start_fails_fast_without_axl_binary(tmp_path: Path) -> None:
    """Spawner refuses to spawn when axl_bin does not exist or is not
    executable. SimController.start surfaces that error rather than
    silently falling back to a mock or hanging on subprocess.Popen.
    """
    missing_axl = tmp_path / "no_such_binary"
    assert not missing_axl.exists()

    hub = SseHub()
    controller = SimController(
        sim_id="sim_test",
        prompt="a research hackathon",
        config=SimConfig(builders=2, judges=1, designers=1, pace="smoke"),
        hub=hub,
        base_dir=tmp_path / "runs",
        axl_bin=missing_axl,
        orch_url="http://127.0.0.1:8000",
    )

    async def _drive() -> None:
        with pytest.raises(SpawnerError, match="missing or not executable"):
            await controller.start()

    asyncio.run(asyncio.wait_for(_drive(), timeout=5.0))

    # After a failed start the controller's snapshot is still the empty
    # one constructed in __init__; no envelopes were folded.
    snap = controller.snapshot
    assert snap["bounties"] == []
    assert snap["builders"] == []
    assert snap["projects"] == []
    assert snap["verdicts"] == []
