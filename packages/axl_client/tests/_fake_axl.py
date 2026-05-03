"""Stdlib-only fake AXL node for AxlClient tests.

Spins up a ThreadingHTTPServer on an ephemeral localhost port that mimics the
endpoints we use: /topology (GET), /send (POST), /recv (GET). The fake stores
every inbound /send call so tests can assert on what was sent, and lets the
test author inject a queue of envelopes to be returned by /recv.

This is intentionally not a full AXL replica; it captures the contract our
client depends on. The real two-node check is the integration test in commit 07.
"""

from __future__ import annotations

import json
import threading
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


class FakeAxlState:
    """Mutable state shared between the test and the running fake server."""

    def __init__(self) -> None:
        self.topology: dict[str, Any] = {
            "our_ipv6": "200::1",
            "our_public_key": "0" * 64,
            "peers": [],
            "tree": [],
        }
        # /send call log: list of (peer_id, content_type, bytes)
        self.sent: list[tuple[str, str, bytes]] = []
        # /recv queue: deque of (from_peer_id, data) pairs
        self.recv_queue: deque[tuple[str, bytes]] = deque()
        # Per-endpoint forced status overrides for error-path tests.
        self.force_status: dict[str, int] = {}


class _Handler(BaseHTTPRequestHandler):
    """One handler instance per request. State lives on the server."""

    state: FakeAxlState  # populated by _make_handler closure

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        # Silence default access logging; tests do not need it.
        pass

    def _send(self, status: int, body: bytes = b"", headers: dict[str, str] | None = None) -> None:
        self.send_response(status)
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    # ------------------------------------------------------------------- GET

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/topology":
            forced = self.state.force_status.get("topology")
            if forced is not None and forced != 200:
                self._send(forced, b"forced")
                return
            body = json.dumps(self.state.topology).encode("utf-8")
            self._send(200, body, {"Content-Type": "application/json"})
            return
        if self.path == "/recv":
            forced = self.state.force_status.get("recv")
            if forced is not None and forced != 200 and forced != 204:
                self._send(forced, b"forced")
                return
            try:
                from_peer, data = self.state.recv_queue.popleft()
            except IndexError:
                self._send(204)
                return
            self._send(200, data, {"X-From-Peer-Id": from_peer})
            return
        self._send(404, b"not found")

    # ------------------------------------------------------------------- POST

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/send":
            forced = self.state.force_status.get("send")
            if forced is not None and forced != 200:
                self._send(forced, b"forced")
                return
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length > 0 else b""
            peer = self.headers.get("X-Destination-Peer-Id", "")
            ctype = self.headers.get("Content-Type", "")
            self.state.sent.append((peer, ctype, body))
            self._send(200, b"", {"X-Sent-Bytes": str(len(body))})
            return
        self._send(404, b"not found")


def _make_handler(state: FakeAxlState):
    cls = type("BoundHandler", (_Handler,), {"state": state})
    return cls


class FakeAxl:
    """Context-managed fake AXL node.

    Usage:
        with FakeAxl() as fake:
            client = AxlClient(fake.url)
            ...
            assert fake.state.sent == [...]
    """

    def __init__(self) -> None:
        self.state = FakeAxlState()
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        if self._server is None:
            raise RuntimeError("FakeAxl not started")
        host, port = self._server.server_address[0], self._server.server_address[1]
        return f"http://{host}:{port}"

    def __enter__(self) -> FakeAxl:
        handler_cls = _make_handler(self.state)
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
