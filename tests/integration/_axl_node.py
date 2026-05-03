"""Helper for booting real AXL node binaries inside integration tests.

The unit ring (commits 04-06) tests our modules against the stdlib FakeAxl
fixture. The integration ring promotes that proof: it boots two real node
binaries on the same loopback, peers them through a single bootstrap, and
exchanges one envelope between them.

Tests that use this helper require the AXL binary to exist at
third_party/axl/node. They are skipped if it does not.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
AXL_BIN = REPO_ROOT / "third_party" / "axl" / "node"


def axl_binary_available() -> bool:
    return AXL_BIN.exists() and os.access(AXL_BIN, os.X_OK)


def _free_port() -> int:
    """Bind a transient port on 127.0.0.1 to find one the OS will not give to AXL."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _gen_ed25519_pem(target: Path) -> None:
    """Generate an ed25519 private key in PEM at `target`. Requires openssl on PATH."""
    if shutil.which("openssl") is None:
        raise RuntimeError("openssl is required to generate AXL identities")
    subprocess.run(
        ["openssl", "genpkey", "-algorithm", "ed25519", "-out", str(target)],
        check=True,
        capture_output=True,
    )


@dataclass
class NodeHandle:
    """A running AXL node subprocess plus the metadata you need to talk to it."""

    name: str
    process: subprocess.Popen
    api_port: int
    tcp_port: int
    listen_uri: str | None
    config_path: Path
    work_dir: Path

    @property
    def api_url(self) -> str:
        return f"http://127.0.0.1:{self.api_port}"

    def stop(self, timeout: float = 5.0) -> None:
        if self.process.poll() is not None:
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=timeout)


def _wait_for_api(api_url: str, deadline: float) -> None:
    """Poll GET /topology until it returns 200 or `deadline` passes."""
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


@contextmanager
def axl_node(
    *,
    name: str,
    work_dir: Path,
    api_port: int,
    tcp_port: int,
    listen_uri: str | None = None,
    peers: list[str] | None = None,
    startup_timeout: float = 30.0,
    mcp_router_addr: str | None = None,
    mcp_router_port: int | None = None,
) -> Iterator[NodeHandle]:
    """Boot one AXL node subprocess. Yields a NodeHandle. Always stops on exit.

    `mcp_router_addr` plus `mcp_router_port` configure the AXL binary to
    forward inbound `/mcp/{peer}/{service}` traffic to that local URL,
    used by the MCP integration test.
    """
    if not axl_binary_available():
        raise RuntimeError(f"AXL binary missing at {AXL_BIN}; run scripts/build_axl.sh")

    work_dir.mkdir(parents=True, exist_ok=True)
    key_path = work_dir / f"{name}.pem"
    _gen_ed25519_pem(key_path)

    config: dict = {
        "PrivateKeyPath": str(key_path),
        "Peers": list(peers or []),
        "Listen": [listen_uri] if listen_uri else [],
        "api_port": api_port,
        "tcp_port": tcp_port,
    }
    if mcp_router_addr is not None and mcp_router_port is not None:
        config["router_addr"] = mcp_router_addr
        config["router_port"] = mcp_router_port
    config_path = work_dir / f"{name}-config.json"
    config_path.write_text(json.dumps(config, indent=2))

    log_path = work_dir / f"{name}.log"
    log_file = open(log_path, "w")

    process = subprocess.Popen(
        [str(AXL_BIN), "-config", str(config_path)],
        stdout=log_file,
        stderr=subprocess.STDOUT,
        cwd=work_dir,
    )

    handle = NodeHandle(
        name=name,
        process=process,
        api_port=api_port,
        tcp_port=tcp_port,
        listen_uri=listen_uri,
        config_path=config_path,
        work_dir=work_dir,
    )

    try:
        _wait_for_api(handle.api_url, deadline=time.time() + startup_timeout)
        yield handle
    finally:
        handle.stop()
        log_file.close()
