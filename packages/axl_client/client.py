"""AxlClient: stdlib urllib wrapper for the AXL node HTTP API.

The HackSim role workers, the orchestrator, and the hacksim-network skill all
talk to a local AXL binary on 127.0.0.1:9002 (or the API port configured for
that role). This module is the single place that knows how to do that.

Ported from collaborative-autoresearch-demo/skills/autoresearch-network/research_network.py:
- _post and _get shape comes from research_network.py:71-130
- send/recv envelope handling matches research_network.py:285-374

Endpoints exercised here:
- GET  /topology   ->  identity, direct peers, spanning tree
- POST /send       ->  unicast bytes to a peer id
- GET  /recv       ->  drain one inbound message from the local queue (204 if empty)

Peer enumeration (all_peer_ids, dedupe of self) lands in commit 06.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

DEFAULT_TIMEOUT = 30.0


class AxlError(RuntimeError):
    """Raised when the local AXL node returns an unexpected status."""

    def __init__(self, message: str, *, status: int | None = None, body: bytes | None = None):
        super().__init__(message)
        self.status = status
        self.body = body


@dataclass(frozen=True)
class PeerInfo:
    """One entry from the topology response. Same shape for `peers[]` and `tree[]`."""

    public_key: str
    up: bool


@dataclass(frozen=True)
class Topology:
    """Decoded /topology response, with the four upstream fields preserved."""

    our_ipv6: str
    our_public_key: str
    peers: list[PeerInfo]
    tree: list[PeerInfo]


@dataclass(frozen=True)
class ReceivedMessage:
    """One inbound message drained from /recv. Empty queue surfaces as None."""

    from_peer_id: str
    data: bytes


def _post(
    url: str,
    data: bytes,
    headers: dict[str, str],
    timeout: float = DEFAULT_TIMEOUT,
) -> tuple[int, dict[str, str], bytes]:
    """POST `data` to `url` and return (status, headers, body) using urllib.

    Mirrors research_network.py:71-130. HTTPError is caught and surfaced as a
    non-200 status so callers do not need to catch.
    """
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as e:
        body = b""
        try:
            body = e.read() or b""
        except Exception:
            pass
        return e.code, dict(e.headers or {}), body


def _get(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> tuple[int, dict[str, str], bytes]:
    """GET `url` and return (status, headers, body) using urllib."""
    req = urllib.request.Request(url, headers=headers or {}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as e:
        body = b""
        try:
            body = e.read() or b""
        except Exception:
            pass
        return e.code, dict(e.headers or {}), body


class AxlClient:
    """Talks to a local AXL node over its HTTP API.

    Construct with the local API URL, for example "http://127.0.0.1:9002".
    The instance is thread-safe by virtue of being stateless; every call is a
    fresh urllib request.
    """

    def __init__(self, api_url: str, *, timeout: float = DEFAULT_TIMEOUT):
        if not api_url.startswith(("http://", "https://")):
            raise ValueError("api_url must include a scheme (http:// or https://)")
        self.api_url = api_url.rstrip("/")
        self.timeout = timeout

    # ------------------------------------------------------------------ topology

    def get_topology(self) -> Topology:
        """GET /topology, return a decoded Topology dataclass.

        Raises AxlError if the node is unreachable or returns non-200.
        """
        status, _, body = _get(f"{self.api_url}/topology", timeout=self.timeout)
        if status != 200:
            raise AxlError(
                f"GET /topology returned {status}", status=status, body=body
            )
        try:
            obj: dict[str, Any] = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise AxlError("/topology body was not valid UTF-8 JSON") from e
        return _decode_topology(obj)

    # ---------------------------------------------------------------------- send

    def send(
        self,
        peer_id: str,
        data: bytes,
        *,
        content_type: str = "application/octet-stream",
    ) -> int:
        """POST /send with `data` to the given peer id. Returns bytes sent.

        Raises AxlError on non-200. The hex peer id format is enforced upstream
        by AXL's HandleSend (axl/api/send.go:30-85); we do not validate here.
        """
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError("data must be bytes-like")
        headers = {
            "X-Destination-Peer-Id": peer_id,
            "Content-Type": content_type,
        }
        status, resp_headers, body = _post(
            f"{self.api_url}/send",
            data=bytes(data),
            headers=headers,
            timeout=self.timeout,
        )
        if status != 200:
            raise AxlError(
                f"POST /send returned {status}", status=status, body=body
            )
        # Header is "X-Sent-Bytes" per axl/api/send.go. urllib lowercases.
        sent = resp_headers.get("X-Sent-Bytes") or resp_headers.get("x-sent-bytes")
        if sent is None:
            return len(data)
        try:
            return int(sent)
        except ValueError:
            return len(data)

    # ---------------------------------------------------------------------- recv

    def recv(self) -> ReceivedMessage | None:
        """GET /recv. Returns one ReceivedMessage, or None when the queue is empty.

        AXL signals empty with HTTP 204. Any other non-200 raises AxlError.
        """
        status, headers, body = _get(f"{self.api_url}/recv", timeout=self.timeout)
        if status == 204:
            return None
        if status != 200:
            raise AxlError(
                f"GET /recv returned {status}", status=status, body=body
            )
        from_peer = headers.get("X-From-Peer-Id") or headers.get("x-from-peer-id") or ""
        return ReceivedMessage(from_peer_id=from_peer, data=body)


def _decode_topology(obj: dict[str, Any]) -> Topology:
    """Translate a /topology JSON object into a Topology dataclass.

    Unknown fields are tolerated; missing required fields raise AxlError.
    """
    if not isinstance(obj, dict):
        raise AxlError("/topology body was not a JSON object")

    def _peer(entry: Any) -> PeerInfo | None:
        if not isinstance(entry, dict):
            return None
        pk = entry.get("public_key")
        if not isinstance(pk, str):
            return None
        up = bool(entry.get("up", True))
        return PeerInfo(public_key=pk, up=up)

    raw_peers = obj.get("peers") or []
    raw_tree = obj.get("tree") or []
    peers = [p for p in (_peer(e) for e in raw_peers) if p is not None]
    tree = [p for p in (_peer(e) for e in raw_tree) if p is not None]
    return Topology(
        our_ipv6=str(obj.get("our_ipv6", "")),
        our_public_key=str(obj.get("our_public_key", "")),
        peers=peers,
        tree=tree,
    )
