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

The Spawner manages two process trees per role node: the AXL Go binary on a
per-node config file, and the Python role worker spawned via
`python -m packages.agents.worker` with the role's env vars set. Claude Code
sessions are not part of the default demo path; if a future commit wires the
opt-in Claude Code variant, it would replace the Python worker subprocess
without touching the AXL node lifecycle.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import signal
import subprocess
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

DEFAULT_BOOTSTRAP_LISTEN = "tls://127.0.0.1:9100"
DEFAULT_API_PORT_BASE = 9200
DEFAULT_TCP_PORT = 7000
DEFAULT_STARTUP_TIMEOUT = 30.0
DEFAULT_MCP_ROUTER_PORT_BASE = 9400


class SpawnerError(RuntimeError):
    """Raised when a node fails to spawn or never becomes ready."""


@dataclass
class NodeSpec:
    """Describes one role node we want to bring up.

    `name` is the human label used for files and logs (e.g. "organiser",
    "designer.0", "builder.4"). It must be filesystem-safe.

    `mcp_router_port`, when set, configures this node's AXL binary to
    forward inbound `/mcp/{peer}/{service}` requests to a local Python
    MCP service running on `127.0.0.1:<mcp_router_port>/route`. Judges
    use this to expose typed JSON-RPC scoring without relinquishing the
    envelope-based control plane.
    """

    name: str
    is_bootstrap: bool = False
    api_port: int | None = None  # auto-allocated if None
    tcp_port: int = DEFAULT_TCP_PORT
    listen_uri: str | None = None  # auto-set to bootstrap URI when is_bootstrap
    mcp_router_port: int | None = None


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
    log_file: Any = None
    mcp_router_port: int | None = None

    @property
    def api_url(self) -> str:
        return f"http://127.0.0.1:{self.api_port}"

    def is_running(self) -> bool:
        return self.process.poll() is None

    def stop(self, timeout: float = 5.0) -> None:
        if self.is_running():
            self.process.terminate()
            try:
                self.process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=timeout)
        self._close_log()

    def _close_log(self) -> None:
        f = self.log_file
        if f is None:
            return
        try:
            f.close()
        except Exception:
            pass
        self.log_file = None


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
    worker_log_file: Any = None

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
        # Close the worker log file handle before the node stop fires
        # (which closes the AXL node log handle). Without this the file
        # descriptor leaks for the lifetime of the orchestrator; over a
        # long session each new sim leaks 15 fds.
        self._close_worker_log()
        self.node.stop(timeout=timeout)

    def _close_worker_log(self) -> None:
        f = self.worker_log_file
        if f is None:
            return
        try:
            f.close()
        except Exception:
            pass
        self.worker_log_file = None


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
        mcp_router_port_base: int = DEFAULT_MCP_ROUTER_PORT_BASE,
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
        self.mcp_router_port_base = mcp_router_port_base
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
        self._next_mcp_port = mcp_router_port_base
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

        config: dict[str, Any] = {
            "PrivateKeyPath": str(key_path),
            "Peers": peers,
            "Listen": [listen_uri] if listen_uri else [],
            "api_port": api_port,
            "tcp_port": spec.tcp_port,
        }
        if spec.mcp_router_port is not None:
            # AXL forwards inbound /mcp/{peer}/{service} traffic to
            # http://<router_addr>:<router_port>/route. We always run
            # the router locally so the address is fixed; the port is
            # spawner-allocated to avoid collisions on the loopback.
            config["router_addr"] = "http://127.0.0.1"
            config["router_port"] = spec.mcp_router_port
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
            log_file=log_file,
            mcp_router_port=spec.mcp_router_port,
        )

        try:
            self._wait_ready(handle.api_url, deadline=time.time() + self.startup_timeout)
        except Exception as e:
            # `handle.stop()` closes the log file via _close_log, so we do
            # not need to close it again here. (Previously this path closed
            # log_file twice, masking the real issue if the second close
            # raised.)
            handle.stop()
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
        extra_env: dict[str, str] | None = None,
        with_mcp_router: bool = False,
    ) -> RoleHandle:
        """Boot one AXL node + one Python role worker process.

        The worker subprocess runs `python -m packages.agents.worker` with
        AXL_API_PORT, HACKSIM_ROLE, HACKSIM_SIM_ID exported. Stdout is
        captured to `<work_dir>/<role>.<index>.worker.log` so the
        orchestrator can tail it for SSE.

        `extra_env` is a per-sim env overlay that takes precedence over the
        orchestrator's own environment. Used to plumb a user-supplied
        Anthropic API key into role workers without touching the host's
        process env.
        """
        name = role if index == 0 and is_bootstrap else f"{role}.{index}"
        mcp_router_port: int | None = None
        if with_mcp_router:
            mcp_router_port = self._allocate_mcp_router_port()
        node = self.spawn(
            NodeSpec(
                name=name,
                is_bootstrap=is_bootstrap,
                mcp_router_port=mcp_router_port,
            )
        )

        repo_root = repo_root or _find_repo_root()
        env = {
            **os.environ,
            "AXL_API_PORT": str(node.api_port),
            "HACKSIM_ROLE": role,
            "HACKSIM_SIM_ID": self.sim_id,
            "HACKSIM_WORK_DIR": str(node.work_dir),
            "PYTHONPATH": f"{repo_root}{os.pathsep}{os.environ.get('PYTHONPATH', '')}".rstrip(os.pathsep),
        }
        if mcp_router_port is not None:
            # The role worker reads HACKSIM_MCP_ROUTER_PORT and starts the
            # MCP service on that port if it knows how (judges do; other
            # roles ignore it).
            env["HACKSIM_MCP_ROUTER_PORT"] = str(mcp_router_port)
        if self.orch_url:
            env["HACKSIM_ORCH_URL"] = self.orch_url
        if extra_env:
            # Per-sim secrets land last so they win over any host env vars.
            env.update(extra_env)

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
            worker_log_file=worker_log_file,
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

    def kill_all(self, wait_timeout: float = 0.3) -> None:
        """SIGKILL every worker and node, then briefly reap. Faster than
        stop_all because it skips the SIGTERM grace period and the
        sequential per-process wait. Used by SimController.stop_fast when
        a new sim is starting and the priority is freeing the bootstrap
        port over flushing final worker.stopped events.
        """
        procs: list[subprocess.Popen] = []
        for r in self._roles:
            if r.worker.poll() is None:
                try:
                    r.worker.send_signal(signal.SIGKILL)
                    procs.append(r.worker)
                except Exception:
                    pass
            if r.node.is_running():
                try:
                    r.node.process.send_signal(signal.SIGKILL)
                    procs.append(r.node.process)
                except Exception:
                    pass
        role_ids = {id(r.node) for r in self._roles}
        for h in self._handles:
            if id(h) in role_ids:
                continue
            if h.is_running():
                try:
                    h.process.send_signal(signal.SIGKILL)
                    procs.append(h.process)
                except Exception:
                    pass
        for p in procs:
            try:
                p.wait(timeout=wait_timeout)
            except Exception:
                pass
        # Close worker log fds so the tailers see EOF promptly.
        for r in self._roles:
            close_fn = getattr(r, "worker_log_file", None)
            if close_fn is not None:
                try:
                    r.worker_log_file.close()  # type: ignore[union-attr]
                except Exception:
                    pass
        self._roles.clear()
        self._handles.clear()
        self._bootstrap_seen = False

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

    def _allocate_mcp_router_port(self) -> int:
        """Hand out the next free MCP router port, kept on a separate
        block from the API ports so a stale loopback bind does not
        cascade into both pools."""
        candidate = self._next_mcp_port
        for _ in range(64):
            if _port_is_free(candidate):
                self._next_mcp_port = candidate + 1
                return candidate
            candidate += 1
        raise SpawnerError(
            f"could not allocate a free MCP router port near {self._next_mcp_port}"
        )


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
