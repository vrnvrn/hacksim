"""Integration test: real AXL nodes route a JSON-RPC call across the mesh.

Two real AXL Go binaries are booted with distinct ed25519 identities.
Bob is configured with a `router_addr`/`router_port` that points at a
local aiohttp service running the judge MCP router. Alice calls
`POST /mcp/<bob_peer>/judge` with a JSON-RPC `tools/call` request, the
MCP bridge tunnels the wrapped envelope through Yggdrasil to Bob's
TCP listener, Bob's MCP stream side-car POSTs to the configured router
URL, the router runs `score_project`, and the response travels back.

Skipped when the AXL binary or openssl is missing. Slow (~10s).
"""

from __future__ import annotations

import asyncio
import shutil
import threading
import time

import pytest

aiohttp = pytest.importorskip("aiohttp")

from packages.agents.judge.mcp_service import (
    SCORE_TOOL,
    SERVICE_NAME,
    build_app,
)
from packages.axl_client import AxlClient

from ._axl_node import axl_binary_available, axl_node


pytestmark = [
    pytest.mark.skipif(
        not axl_binary_available(),
        reason="AXL binary not built; run scripts/build_axl.sh",
    ),
    pytest.mark.skipif(
        shutil.which("openssl") is None,
        reason="openssl required to generate ed25519 keys",
    ),
]


def _wait_for_peer(client: AxlClient, target: str, deadline: float) -> None:
    while time.time() < deadline:
        if target in client.all_peer_ids():
            return
        time.sleep(0.5)
    raise TimeoutError(f"peer {target[:16]}... not visible in topology")


class _RouterServer:
    """Run the judge MCP service in a background thread for the duration of the test."""

    def __init__(self, *, judge_peer_id: str, port: int):
        self.judge_peer_id = judge_peer_id
        self.port = port
        self._loop: asyncio.AbstractEventLoop | None = None
        self._runner = None
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._ready = threading.Event()

    def __enter__(self):
        self._thread.start()
        self._ready.wait(timeout=5.0)
        return self

    def __exit__(self, *_):
        if self._loop is not None and self._runner is not None:
            try:
                fut = asyncio.run_coroutine_threadsafe(
                    self._runner.cleanup(), self._loop
                )
                fut.result(timeout=2.0)
            except Exception:
                pass
        if self._loop is not None:
            try:
                self._loop.call_soon_threadsafe(self._loop.stop)
            except Exception:
                pass
        self._thread.join(timeout=2.0)

    def _serve(self):
        from aiohttp import web

        loop = asyncio.new_event_loop()
        self._loop = loop
        asyncio.set_event_loop(loop)
        app = build_app(self.judge_peer_id)
        runner = web.AppRunner(app)
        self._runner = runner
        loop.run_until_complete(runner.setup())
        site = web.TCPSite(runner, "127.0.0.1", self.port)
        loop.run_until_complete(site.start())
        self._ready.set()
        loop.run_forever()


def test_mcp_round_trip_across_two_axl_nodes(tmp_path):
    # Use high random ports so a stale leftover sim from a previous run
    # cannot squat on a fixed bootstrap. _free_port asks the kernel for
    # a port that is currently free and avoids well-known ranges.
    from ._axl_node import _free_port

    bootstrap_port = _free_port()
    bootstrap_uri = f"tls://127.0.0.1:{bootstrap_port}"
    alice_api = _free_port()
    bob_api = _free_port()
    router_port = _free_port()

    # The router's `judge_peer_id` only flavours the response; any
    # 64-hex string is safe to pre-build with. Real runs pass the live
    # peer id sourced from /topology.
    placeholder_judge_peer = "0" * 64

    # Alice is the bootstrap AND the judge: Bob dials Alice, sees her
    # in his topology, and calls her MCP service. (Doing the reverse
    # would require Alice to discover Bob without Bob being the
    # bootstrap, which the spanning tree does eventually but is slower
    # and racier inside a 30-second test.)
    with axl_node(
        name="alice",
        work_dir=tmp_path / "alice",
        api_port=alice_api,
        tcp_port=7000,
        listen_uri=bootstrap_uri,
        mcp_router_addr="http://127.0.0.1",
        mcp_router_port=router_port,
    ) as alice, axl_node(
        name="bob",
        work_dir=tmp_path / "bob",
        api_port=bob_api,
        tcp_port=7000,
        peers=[bootstrap_uri],
    ) as bob, _RouterServer(
        judge_peer_id=placeholder_judge_peer, port=router_port
    ):
        alice_client = AxlClient(alice.api_url)
        bob_client = AxlClient(bob.api_url)

        alice_peer = alice_client.get_topology().our_public_key
        assert len(alice_peer) == 64

        deadline = time.time() + 30.0
        _wait_for_peer(bob_client, alice_peer, deadline)

        # Bob calls Alice's MCP service over the mesh.
        rpc_body = {
            "jsonrpc": "2.0",
            "id": "rpc-1",
            "method": "tools/call",
            "params": {
                "name": SCORE_TOOL,
                "arguments": {
                    "project": {
                        "project_id": "proj_round_trip",
                        "title": "Demo",
                        "files": [],
                    },
                    "bounty": {
                        "title": "Best Demo",
                        "sponsor_name": "Helix Capital",
                    },
                },
            },
        }
        reply = bob_client.mcp_call(alice_peer, SERVICE_NAME, rpc_body, timeout=20.0)

        # AXL's bridge unwraps the MCP envelope before returning to us, so
        # the body shape is the inner JSON-RPC reply directly.
        assert "result" in reply or "error" in reply
        result = reply.get("result")
        assert result is not None, f"unexpected error reply: {reply}"
        verdict = result["structuredContent"]
        assert verdict["project_id"] == "proj_round_trip"
        assert verdict["judge_peer_id"] == placeholder_judge_peer
        assert "scores" in verdict
