"""Spawn and supervise AXL node subprocesses for a HackSim simulation.

Generalises the axl_node helper from commit 07: instead of one or two ad-hoc
nodes, the Spawner manages a population of named role nodes peered through a
single loopback bootstrap.

Topology pattern, identical to the autoresearch demo's local mode:

    organiser   <-- "bootstrap"  Listen=["tls://127.0.0.1:9100"], Peers=[]
    designer.0  <-- Peers=["tls://127.0.0.1:9100"]
    designer.1  <-- Peers=["tls://127.0.0.1:9100"]
    builder.0   <-- Peers=["tls://127.0.0.1:9100"]
    ...

All non-bootstrap nodes dial the same bootstrap URI. Yggdrasil discovers them
to each other through the spanning tree. Each node reads /topology to find
the others by hex peer id.

API ports are allocated from a base (9200 default) plus the running index.
TCP ports all share the default 7000 (see commit 07 for why this is correct).

The Spawner does not start Claude Code sessions; that lands in commit 12 once
the hacksim-network skill (commit 11) is in place.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

DEFAULT_BOOTSTRAP_LISTEN = "tls://127.0.0.1:9100"
DEFAULT_API_PORT_BASE = 9200
DEFAULT_TCP_PORT = 7000
DEFAULT_STARTUP_TIMEOUT = 30.0


class SpawnerError(RuntimeError):
    """Raised when a node fails to spawn or never becomes ready."""


@dataclass
class NodeSpec:
    """Describes one role node we want to bring up.

    `name` is the human label used for files and logs (e.g. "organiser",
    "designer.0", "builder.4"). It must be filesystem-safe.
    """

    name: str
    is_bootstrap: bool = False
    api_port: int | None = None  # auto-allocated if None
    tcp_port: int = DEFAULT_TCP_PORT
    listen_uri: str | None = None  # auto-set to bootstrap URI when is_bootstrap


@dataclass
class NodeHandle:
    """A running AXL node. Returned by Spawner.spawn for use by the rest of the orchestrator."""

    spec: NodeSpec
    process: subprocess.Popen
    api_port: int
    tcp_port: int
    listen_uri: str | None
    work_dir: Path
    config_path: Path
    log_path: Path

    @property
    def api_url(self) -> str:
        return f"http://127.0.0.1:{self.api_port}"

    def is_running(self) -> bool:
        return self.process.poll() is None

    def stop(self, timeout: float = 5.0) -> None:
        if not self.is_running():
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=timeout)


@dataclass
class RoleHandle:
    """A running role: one AXL node plus one Python worker process.

    The worker process is launched with three env vars set:
    AXL_API_PORT, HACKSIM_ROLE, HACKSIM_SIM_ID. It dispatches by role
    inside packages/agents/worker.py.
    """

    node: NodeHandle
    worker: subprocess.Popen
    role: str
    sim_id: str
    worker_log_path: Path

    @property
    def api_url(self) -> str:
        return self.node.api_url

    def is_running(self) -> bool:
        return self.node.is_running() and self.worker.poll() is None

    def stop(self, timeout: float = 5.0) -> None:
        # Stop the worker first so it gets a clean SIGTERM and emits
        # worker.stopped before the AXL node disappears underneath it.
        if self.worker.poll() is None:
            self.worker.terminate()
            try:
                self.worker.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                self.worker.kill()
                self.worker.wait(timeout=timeout)
        self.node.stop(timeout=timeout)


class Spawner:
    """Brings up and tears down a population of AXL nodes for one simulation.

    Usage:

        with Spawner(base_dir=Path("sim-runs/sim_x"), axl_bin=AXL_BIN) as spawner:
            organiser = spawner.spawn(NodeSpec(name="organiser", is_bootstrap=True))
            for i in range(3):
                spawner.spawn(NodeSpec(name=f"designer.{i}"))
            ...
            # nodes are running; do work; .stop_all() runs on exit.
    """

    def __init__(
        self,
        *,
        base_dir: Path,
        axl_bin: Path,
        bootstrap_listen: str = DEFAULT_BOOTSTRAP_LISTEN,
        api_port_base: int = DEFAULT_API_PORT_BASE,
        startup_timeout: float = DEFAULT_STARTUP_TIMEOUT,
        python_bin: str | None = None,
        sim_id: str = "sim_default",
        orch_url: str | None = None,
        keygen: callable | None = None,
        popen: callable | None = None,
        wait_ready: callable | None = None,
    ):
        self.base_dir = base_dir
        self.axl_bin = axl_bin
        self.bootstrap_listen = bootstrap_listen
        self.api_port_base = api_port_base
        self.startup_timeout = startup_timeout
        self.python_bin = python_bin or _find_python()
        self.sim_id = sim_id
        self.orch_url = orch_url
        self._keygen = keygen or _gen_ed25519_pem
        self._popen = popen or subprocess.Popen
        self._wait_ready = wait_ready or _wait_for_api
        self._handles: list[NodeHandle] = []
        self._roles: list[RoleHandle] = []
        self._next_port = api_port_base
        self._bootstrap_seen = False

        if not self.base_dir.exists():
            self.base_dir.mkdir(parents=True)

    # -------------------------------------------------------------------- spawn

    def spawn(self, spec: NodeSpec) -> NodeHandle:
        """Boot one AXL node per the given spec. Returns a live NodeHandle."""
        if spec.is_bootstrap and self._bootstrap_seen:
            raise SpawnerError("only one bootstrap node is allowed per Spawner")

        if not (self.axl_bin.exists() and os.access(self.axl_bin, os.X_OK)):
            raise SpawnerError(f"AXL binary missing or not executable: {self.axl_bin}")

        api_port = spec.api_port if spec.api_port is not None else self._allocate_port()
        listen_uri = spec.listen_uri
        peers: list[str] = []
        if spec.is_bootstrap:
            listen_uri = listen_uri or self.bootstrap_listen
        else:
            peers = [self.bootstrap_listen]

        work_dir = self.base_dir / spec.name
        work_dir.mkdir(parents=True, exist_ok=True)
        key_path = work_dir / f"{spec.name}.pem"
        self._keygen(key_path)

        config = {
            "PrivateKeyPath": str(key_path),
            "Peers": peers,
            "Listen": [listen_uri] if listen_uri else [],
            "api_port": api_port,
            "tcp_port": spec.tcp_port,
        }
        config_path = work_dir / f"{spec.name}-config.json"
        config_path.write_text(json.dumps(config, indent=2))

        log_path = work_dir / f"{spec.name}.log"
        log_file = open(log_path, "w")

        try:
            process = self._popen(
                [str(self.axl_bin), "-config", str(config_path)],
                stdout=log_file,
                stderr=subprocess.STDOUT,
                cwd=work_dir,
            )
        except Exception as e:
            log_file.close()
            raise SpawnerError(f"failed to launch {spec.name}: {e}") from e

        handle = NodeHandle(
            spec=spec,
            process=process,
            api_port=api_port,
            tcp_port=spec.tcp_port,
            listen_uri=listen_uri,
            work_dir=work_dir,
            config_path=config_path,
            log_path=log_path,
        )

        try:
            self._wait_ready(handle.api_url, deadline=time.time() + self.startup_timeout)
        except Exception as e:
            handle.stop()
            log_file.close()
            raise SpawnerError(f"{spec.name} did not become ready: {e}") from e

        self._handles.append(handle)
        if spec.is_bootstrap:
            self._bootstrap_seen = True
        return handle

    # ---------------------------------------------------------------- spawn_role

    def spawn_role(
        self,
        *,
        role: str,
        index: int = 0,
        is_bootstrap: bool = False,
        repo_root: Path | None = None,
    ) -> RoleHandle:
        """Boot one AXL node + one Python role worker process.

        The worker subprocess runs `python -m packages.agents.worker` with
        AXL_API_PORT, HACKSIM_ROLE, HACKSIM_SIM_ID exported. Stdout is
        captured to `<work_dir>/<role>.<index>.worker.log` so the
        orchestrator can tail it for SSE.
        """
        name = role if index == 0 and is_bootstrap else f"{role}.{index}"
        node = self.spawn(NodeSpec(name=name, is_bootstrap=is_bootstrap))

        repo_root = repo_root or _find_repo_root()
        env = {
            **os.environ,
            "AXL_API_PORT": str(node.api_port),
            "HACKSIM_ROLE": role,
            "HACKSIM_SIM_ID": self.sim_id,
            "HACKSIM_WORK_DIR": str(node.work_dir),
            "PYTHONPATH": f"{repo_root}{os.pathsep}{os.environ.get('PYTHONPATH', '')}".rstrip(os.pathsep),
        }
        if self.orch_url:
            env["HACKSIM_ORCH_URL"] = self.orch_url

        worker_log = node.work_dir / f"{name}.worker.log"
        worker_log_file = open(worker_log, "w")

        try:
            worker = self._popen(
                [self.python_bin, "-m", "packages.agents.worker"],
                stdout=worker_log_file,
                stderr=subprocess.STDOUT,
                cwd=repo_root,
                env=env,
            )
        except Exception as e:
            worker_log_file.close()
            node.stop()
            raise SpawnerError(f"failed to launch worker for {name}: {e}") from e

        handle = RoleHandle(
            node=node,
            worker=worker,
            role=role,
            sim_id=self.sim_id,
            worker_log_path=worker_log,
        )
        self._roles.append(handle)
        return handle

    # --------------------------------------------------------------- lifecycle

    @property
    def handles(self) -> list[NodeHandle]:
        return list(self._handles)

    @property
    def role_handles(self) -> list[RoleHandle]:
        return list(self._roles)

    def stop_all(self, timeout: float = 5.0) -> None:
        """Stop every spawned role and node. Workers first (so they emit
        worker.stopped), then nodes in reverse spawn order so the
        bootstrap goes last."""
        for r in reversed(self._roles):
            try:
                r.stop(timeout=timeout)
            except Exception:
                pass
        self._roles.clear()
        # Stop any nodes that were spawned without a role (rare).
        nodes_with_role_ids = {id(r.node) for r in self._roles}
        for h in reversed(self._handles):
            if id(h) in nodes_with_role_ids:
                continue
            try:
                h.stop(timeout=timeout)
            except Exception:
                pass
        self._handles.clear()
        self._bootstrap_seen = False

    def __enter__(self) -> "Spawner":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop_all()

    # ------------------------------------------------------------------ ports

    def _allocate_port(self) -> int:
        """Hand out the next API port, skipping any the OS already has bound."""
        candidate = self._next_port
        for _ in range(64):
            if _port_is_free(candidate):
                self._next_port = candidate + 1
                return candidate
            candidate += 1
        raise SpawnerError(f"could not allocate a free port near {self._next_port}")


# ---------------------------------------------------------------------- helpers


def _port_is_free(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", port))
            return True
    except OSError:
        return False


def _gen_ed25519_pem(target: Path) -> None:
    if shutil.which("openssl") is None:
        raise SpawnerError("openssl is required to generate AXL identities")
    subprocess.run(
        ["openssl", "genpkey", "-algorithm", "ed25519", "-out", str(target)],
        check=True,
        capture_output=True,
    )


def _wait_for_api(api_url: str, deadline: float) -> None:
    """Poll GET /topology until 200 or `deadline` passes."""
    import urllib.error
    import urllib.request

    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{api_url}/topology", timeout=0.5) as r:
                if r.status == 200:
                    return
        except (urllib.error.URLError, ConnectionError, OSError):
            pass
        time.sleep(0.1)
    raise TimeoutError(f"AXL node at {api_url} did not become ready before deadline")


def _find_python() -> str:
    """Return a path to the Python executable to use for role workers.

    Prefers the venv that runs the orchestrator, falling back to the
    interpreter on PATH. The role workers must use the same env so
    the packages namespace resolves.
    """
    import sys
    return sys.executable


def _find_repo_root() -> Path:
    """Find the HackSim repo root from this module's location."""
    return Path(__file__).resolve().parents[2]
