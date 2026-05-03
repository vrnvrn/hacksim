"""Unit tests for the Spawner. The subprocess and key generation hooks are
injected so the tests do not require a real AXL binary or openssl.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from packages.orchestrator import NodeSpec, Spawner, SpawnerError


@pytest.fixture
def fake_axl_bin(tmp_path: Path) -> Path:
    """A fake AXL binary that exists and is executable but does nothing."""
    bin_path = tmp_path / "axl_bin"
    bin_path.write_text("#!/bin/sh\nsleep 60\n")
    bin_path.chmod(0o755)
    return bin_path


@pytest.fixture
def fake_keygen():
    """Substitute for openssl. Writes a dummy PEM file."""

    def keygen(target: Path) -> None:
        target.write_text("-----BEGIN PRIVATE KEY-----\nfake\n-----END PRIVATE KEY-----\n")

    return keygen


@pytest.fixture
def fake_popen():
    """Substitute for subprocess.Popen. Returns a MagicMock; records args+kwargs."""
    processes: list[MagicMock] = []
    calls: list[dict] = []

    def popen(*args, **kwargs):
        proc = MagicMock()
        proc.pid = 12000 + len(processes)
        proc.poll.return_value = None  # still running
        proc.wait.return_value = 0
        proc.terminate = MagicMock()
        proc.kill = MagicMock()
        processes.append(proc)
        calls.append({"args": args, "kwargs": kwargs})
        return proc

    popen.processes = processes  # type: ignore[attr-defined]
    popen.calls = calls  # type: ignore[attr-defined]
    return popen


@pytest.fixture
def instant_ready():
    """Substitute for _wait_for_api. Returns immediately."""

    def ready(api_url: str, deadline: float) -> None:
        return None

    return ready


@pytest.fixture
def spawner(tmp_path, fake_axl_bin, fake_keygen, fake_popen, instant_ready):
    return Spawner(
        base_dir=tmp_path / "sim",
        axl_bin=fake_axl_bin,
        keygen=fake_keygen,
        popen=fake_popen,
        wait_ready=instant_ready,
    )


class TestSpawnLifecycle:
    def test_spawn_bootstrap_then_peer(self, spawner, fake_popen):
        bootstrap = spawner.spawn(NodeSpec(name="organiser", is_bootstrap=True))
        peer = spawner.spawn(NodeSpec(name="designer.0"))

        assert bootstrap.spec.is_bootstrap is True
        assert peer.spec.is_bootstrap is False
        assert bootstrap.api_port != peer.api_port
        assert bootstrap.work_dir.name == "organiser"
        assert peer.work_dir.name == "designer.0"
        assert len(fake_popen.processes) == 2
        assert bootstrap.is_running()
        assert peer.is_running()

    def test_bootstrap_listens_peers_dial(self, spawner):
        bootstrap = spawner.spawn(NodeSpec(name="organiser", is_bootstrap=True))
        peer = spawner.spawn(NodeSpec(name="builder.0"))

        b_cfg = json.loads(bootstrap.config_path.read_text())
        p_cfg = json.loads(peer.config_path.read_text())

        assert b_cfg["Listen"] == ["tls://127.0.0.1:9100"]
        assert b_cfg["Peers"] == []
        assert p_cfg["Listen"] == []
        assert p_cfg["Peers"] == ["tls://127.0.0.1:9100"]

    def test_only_one_bootstrap_allowed(self, spawner):
        spawner.spawn(NodeSpec(name="organiser", is_bootstrap=True))
        with pytest.raises(SpawnerError, match="one bootstrap node"):
            spawner.spawn(NodeSpec(name="other", is_bootstrap=True))

    def test_keys_and_configs_are_written(self, spawner, fake_keygen):
        h = spawner.spawn(NodeSpec(name="organiser", is_bootstrap=True))
        assert (h.work_dir / "organiser.pem").exists()
        assert h.config_path.exists()
        cfg = json.loads(h.config_path.read_text())
        assert cfg["PrivateKeyPath"].endswith("organiser.pem")
        assert cfg["api_port"] == h.api_port
        assert cfg["tcp_port"] == 7000

    def test_explicit_api_port_overrides_allocation(self, spawner):
        h = spawner.spawn(NodeSpec(name="organiser", is_bootstrap=True, api_port=9555))
        assert h.api_port == 9555
        cfg = json.loads(h.config_path.read_text())
        assert cfg["api_port"] == 9555

    def test_api_ports_increment(self, spawner):
        a = spawner.spawn(NodeSpec(name="organiser", is_bootstrap=True))
        b = spawner.spawn(NodeSpec(name="designer.0"))
        c = spawner.spawn(NodeSpec(name="designer.1"))
        assert b.api_port > a.api_port
        assert c.api_port > b.api_port

    def test_handles_property_returns_a_copy(self, spawner):
        spawner.spawn(NodeSpec(name="organiser", is_bootstrap=True))
        handles = spawner.handles
        handles.clear()  # mutating the copy must not affect spawner state
        assert len(spawner.handles) == 1


class TestStopAll:
    def test_stop_all_terminates_each_handle(self, spawner, fake_popen):
        spawner.spawn(NodeSpec(name="organiser", is_bootstrap=True))
        spawner.spawn(NodeSpec(name="designer.0"))
        spawner.spawn(NodeSpec(name="builder.0"))
        assert len(fake_popen.processes) == 3

        spawner.stop_all()

        for proc in fake_popen.processes:
            proc.terminate.assert_called_once()
        assert spawner.handles == []

    def test_stop_all_idempotent(self, spawner):
        spawner.spawn(NodeSpec(name="organiser", is_bootstrap=True))
        spawner.stop_all()
        spawner.stop_all()  # second call should not error

    def test_context_manager_stops_on_exit(self, tmp_path, fake_axl_bin, fake_keygen, fake_popen, instant_ready):
        with Spawner(
            base_dir=tmp_path / "sim",
            axl_bin=fake_axl_bin,
            keygen=fake_keygen,
            popen=fake_popen,
            wait_ready=instant_ready,
        ) as s:
            s.spawn(NodeSpec(name="organiser", is_bootstrap=True))
            s.spawn(NodeSpec(name="builder.0"))

        for proc in fake_popen.processes:
            proc.terminate.assert_called_once()


class TestErrorPaths:
    def test_missing_binary_raises(self, tmp_path, fake_keygen, fake_popen, instant_ready):
        s = Spawner(
            base_dir=tmp_path / "sim",
            axl_bin=tmp_path / "does_not_exist",
            keygen=fake_keygen,
            popen=fake_popen,
            wait_ready=instant_ready,
        )
        with pytest.raises(SpawnerError, match="missing or not executable"):
            s.spawn(NodeSpec(name="organiser", is_bootstrap=True))

    def test_wait_ready_failure_terminates_node(self, tmp_path, fake_axl_bin, fake_keygen, fake_popen):
        def never_ready(api_url, deadline):
            raise TimeoutError("never ready")

        s = Spawner(
            base_dir=tmp_path / "sim",
            axl_bin=fake_axl_bin,
            keygen=fake_keygen,
            popen=fake_popen,
            wait_ready=never_ready,
        )
        with pytest.raises(SpawnerError, match="did not become ready"):
            s.spawn(NodeSpec(name="organiser", is_bootstrap=True))
        # The popen mock should have been terminated.
        assert len(fake_popen.processes) == 1
        fake_popen.processes[0].terminate.assert_called_once()


class TestSpawnRole:
    def test_spawn_role_starts_axl_node_then_worker(self, spawner, fake_popen):
        handle = spawner.spawn_role(role="organiser", is_bootstrap=True)

        # First popen call: the AXL node. Second: the Python worker.
        assert len(fake_popen.calls) == 2

        node_call = fake_popen.calls[0]
        worker_call = fake_popen.calls[1]

        node_argv = node_call["args"][0]
        assert "axl_bin" in node_argv[0]
        assert "-config" in node_argv

        worker_argv = worker_call["args"][0]
        assert worker_argv[-3:] == ["-m", "packages.agents.worker", ] or (
            "packages.agents.worker" in worker_argv
        )
        assert handle.role == "organiser"
        assert handle.node.is_running()

    def test_worker_env_carries_axl_port_role_sim_id(self, spawner, fake_popen):
        handle = spawner.spawn_role(role="builder", index=4)
        worker_call = fake_popen.calls[1]
        env = worker_call["kwargs"]["env"]
        assert env["AXL_API_PORT"] == str(handle.node.api_port)
        assert env["HACKSIM_ROLE"] == "builder"
        assert env["HACKSIM_SIM_ID"] == spawner.sim_id
        assert "PYTHONPATH" in env

    def test_two_roles_get_distinct_api_ports(self, spawner, fake_popen):
        a = spawner.spawn_role(role="organiser", is_bootstrap=True)
        b = spawner.spawn_role(role="builder", index=0)
        c = spawner.spawn_role(role="builder", index=1)
        ports = {a.node.api_port, b.node.api_port, c.node.api_port}
        assert len(ports) == 3

    def test_role_handles_property(self, spawner, fake_popen):
        spawner.spawn_role(role="organiser", is_bootstrap=True)
        spawner.spawn_role(role="builder", index=0)
        roles = spawner.role_handles
        assert [r.role for r in roles] == ["organiser", "builder"]

    def test_stop_all_terminates_workers_then_nodes(self, spawner, fake_popen):
        spawner.spawn_role(role="organiser", is_bootstrap=True)
        spawner.spawn_role(role="builder", index=0)
        # 2 nodes + 2 workers = 4 popen calls
        assert len(fake_popen.processes) == 4

        spawner.stop_all()

        # All processes should have received terminate.
        for proc in fake_popen.processes:
            proc.terminate.assert_called()
        assert spawner.role_handles == []


class TestPortAllocation:
    def test_skips_ports_already_in_use(self, tmp_path, fake_axl_bin, fake_keygen, fake_popen, instant_ready):
        """If the OS already has port N bound, _allocate_port returns the next free one."""
        import socket

        # Bind a port to make it busy.
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        busy_port = s.getsockname()[1]

        try:
            sp = Spawner(
                base_dir=tmp_path / "sim",
                axl_bin=fake_axl_bin,
                api_port_base=busy_port,
                keygen=fake_keygen,
                popen=fake_popen,
                wait_ready=instant_ready,
            )
            h = sp.spawn(NodeSpec(name="organiser", is_bootstrap=True))
            assert h.api_port != busy_port
        finally:
            s.close()
