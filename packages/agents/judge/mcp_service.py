"""MCP service side-car for a judge worker.

When the spawner allocates a router port for a judge node, the AXL
binary is configured to forward inbound `/mcp/{peer}/{service}` traffic
to `http://127.0.0.1:<router_port>/route`. This module is the small
aiohttp app that listens on that port and answers the JSON-RPC the
caller sent.

Service surface
---------------

One MCP service is exposed: ``judge``. The supported JSON-RPC methods
are the standard ``initialize`` / ``tools/list`` / ``tools/call`` shape
the MCP spec uses. Only one tool is registered: ``score_project``,
arguments ``{project: <project payload>, bounty: <bounty payload>}``.
The handler runs ``decisions.score_project`` synchronously (the
deterministic stub is fast; the Anthropic path is wrapped by the
shared helper with a 10s timeout) and returns the verdict.

Concurrency model
-----------------

The aiohttp app runs in a background daemon thread inside the judge
worker process. Running in-process means we share the worker's
deterministic-stub fallback and the same code path that handles
envelope-based scoring; no separate process boundary, no double-loaded
persona.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from collections.abc import Callable
from typing import Any

from .decisions import score_project

EmitFn = Callable[[str, dict[str, Any]], None]


SERVICE_NAME = "judge"
SCORE_TOOL = "score_project"
PROTOCOL_VERSION = "2024-11-05"

_log = logging.getLogger("hacksim.judge.mcp")


def make_score_handler(judge_peer_id: str, emit: EmitFn | None = None):
    """Return a callable that scores `(project, bounty)` and returns a verdict.

    Centralised so the test harness can drive the same code path that
    the live aiohttp app uses, without spinning up the HTTP server.
    """

    def handler(arguments: dict[str, Any]) -> dict[str, Any]:
        project = arguments.get("project") or {}
        bounty = arguments.get("bounty")
        verdict = score_project(
            project=project,
            bounty=bounty,
            judge_peer_id=judge_peer_id,
            emit=emit,
        )
        return verdict

    return handler


def build_app(judge_peer_id: str, emit: EmitFn | None = None):
    """Build the aiohttp Application that AXL's MCP bridge talks to.

    Lazy-imports `aiohttp` so this module stays importable when the
    optional orchestrator extras are missing (the run-time path that
    needs MCP installs them; the unit-test path that exercises just the
    handler logic does not).
    """
    from aiohttp import web

    score = make_score_handler(judge_peer_id, emit=emit)

    async def handle_route(request):
        try:
            body = await request.json()
        except Exception as e:
            return web.json_response(
                {"response": None, "error": f"invalid JSON: {e}"},
                status=400,
            )
        service = body.get("service", "")
        rpc = body.get("request") or {}

        if service != SERVICE_NAME:
            return web.json_response(
                {"response": None, "error": f"unknown service: {service}"},
                status=404,
            )

        method = rpc.get("method", "")
        rpc_id = rpc.get("id")

        if method == "initialize":
            return _wrap(rpc_id, {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVICE_NAME, "version": "0.0.1"},
            })
        if method == "tools/list":
            return _wrap(rpc_id, {
                "tools": [
                    {
                        "name": SCORE_TOOL,
                        "description": (
                            "Score a project against a bounty using the "
                            "judge's archetype-weighted rubric."
                        ),
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "project": {"type": "object"},
                                "bounty": {"type": "object"},
                            },
                            "required": ["project"],
                        },
                    }
                ]
            })
        if method == "tools/call":
            params = rpc.get("params") or {}
            name = params.get("name", "")
            arguments = params.get("arguments") or {}
            if name != SCORE_TOOL:
                return _wrap_error(rpc_id, -32601, f"unknown tool: {name}")
            try:
                verdict = score(arguments)
            except Exception as e:
                _log.exception("score_project raised")
                return _wrap_error(rpc_id, -32603, f"score failed: {e}")
            # MCP tools/call response wraps results in a `content` array.
            return _wrap(rpc_id, {
                "content": [
                    {"type": "text", "text": json.dumps(verdict)},
                ],
                "structuredContent": verdict,
            })
        return _wrap_error(rpc_id, -32601, f"unknown method: {method}")

    async def handle_health(_request):
        return web.json_response(
            {"status": "ok", "service": SERVICE_NAME, "judge_peer_id": judge_peer_id[:8]}
        )

    app = web.Application()
    app.router.add_post("/route", handle_route)
    app.router.add_get("/health", handle_health)
    return app


def _wrap(rpc_id: Any, result: dict[str, Any]):
    """Wrap a successful JSON-RPC response inside the AXL router envelope."""
    from aiohttp import web

    return web.json_response(
        {
            "response": {"jsonrpc": "2.0", "id": rpc_id, "result": result},
            "error": None,
        }
    )


def _wrap_error(rpc_id: Any, code: int, message: str):
    from aiohttp import web

    return web.json_response(
        {
            "response": {
                "jsonrpc": "2.0",
                "id": rpc_id,
                "error": {"code": code, "message": message},
            },
            "error": None,
        }
    )


class McpService:
    """Run the aiohttp router in a background daemon thread.

    Construct, call `start()` once, call `stop()` on shutdown. Owning
    the lifecycle in a thread keeps the judge's main role loop on the
    main thread (where signal handlers work) while still serving HTTP.
    """

    def __init__(self, *, judge_peer_id: str, port: int, emit: EmitFn | None = None):
        self.judge_peer_id = judge_peer_id
        self.port = port
        self.emit = emit
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._runner = None  # aiohttp web.AppRunner, lazy-typed
        self._ready = threading.Event()
        self._error: BaseException | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(
            target=self._serve, name="hacksim-judge-mcp", daemon=True
        )
        self._thread.start()
        # Block briefly so the caller sees a clean ready state before
        # the simulation starts driving traffic at us.
        if not self._ready.wait(timeout=5.0):
            if self.emit:
                self.emit(
                    "mcp.service_start_failed",
                    {"port": self.port, "reason": "ready timeout"},
                )

    def stop(self) -> None:
        loop = self._loop
        runner = self._runner
        if loop is None or runner is None:
            return
        try:
            asyncio.run_coroutine_threadsafe(runner.cleanup(), loop).result(timeout=2.0)
        except Exception:
            pass
        try:
            loop.call_soon_threadsafe(loop.stop)
        except Exception:
            pass
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self._thread = None
        self._loop = None
        self._runner = None

    def _serve(self) -> None:
        try:
            from aiohttp import web

            loop = asyncio.new_event_loop()
            self._loop = loop
            asyncio.set_event_loop(loop)
            app = build_app(self.judge_peer_id, emit=self.emit)
            runner = web.AppRunner(app)
            self._runner = runner
            loop.run_until_complete(runner.setup())
            site = web.TCPSite(runner, "127.0.0.1", self.port)
            loop.run_until_complete(site.start())
            if self.emit:
                self.emit(
                    "mcp.service_started",
                    {
                        "service": SERVICE_NAME,
                        "port": self.port,
                        "judge_peer_id": self.judge_peer_id[:16],
                    },
                )
            self._ready.set()
            loop.run_forever()
        except BaseException as e:
            self._error = e
            self._ready.set()
            if self.emit:
                self.emit(
                    "mcp.service_start_failed",
                    {"port": self.port, "error": str(e)},
                )
