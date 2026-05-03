"""Unit tests for the judge MCP service.

These tests exercise the JSON-RPC handler logic by driving the aiohttp
application directly with `aiohttp.test_utils`. They do not boot the
AXL Go binary; that is covered by tests/integration/test_mcp_round_trip.py.

What this proves:
- `initialize` returns the protocol version and the service name.
- `tools/list` reports the `score_project` tool with the expected schema.
- `tools/call` with `name=score_project` runs `score_project` and
  returns the verdict in both `content[*].text` (MCP convention) and
  `structuredContent` (the same dict, parsed).
- An unknown method or tool returns a JSON-RPC error envelope, never a
  500 from the HTTP layer.
"""

from __future__ import annotations

import json

import pytest

aiohttp = pytest.importorskip("aiohttp")
from aiohttp.test_utils import TestClient, TestServer  # noqa: E402

from packages.agents.judge.mcp_service import (  # noqa: E402
    SCORE_TOOL,
    SERVICE_NAME,
    build_app,
    make_score_handler,
)

JUDGE_PEER = "j" * 64


@pytest.fixture(autouse=True)
def _no_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


@pytest.fixture
async def client():
    app = build_app(JUDGE_PEER)
    server = TestServer(app)
    async with TestClient(server) as c:
        yield c


def _envelope(method: str, params: dict | None = None, rpc_id: str = "rpc-1") -> dict:
    return {
        "service": SERVICE_NAME,
        "request": {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "method": method,
            "params": params or {},
        },
        "from_peer_id": "p" * 64,
    }


class TestInitialize:
    async def test_returns_protocol_version_and_server_info(self, client):
        r = await client.post("/route", json=_envelope("initialize"))
        assert r.status == 200
        body = await r.json()
        assert body["error"] is None
        result = body["response"]["result"]
        assert "protocolVersion" in result
        assert result["serverInfo"]["name"] == SERVICE_NAME


class TestToolsList:
    async def test_lists_score_project_with_input_schema(self, client):
        r = await client.post("/route", json=_envelope("tools/list"))
        body = await r.json()
        tools = body["response"]["result"]["tools"]
        assert len(tools) == 1
        tool = tools[0]
        assert tool["name"] == SCORE_TOOL
        assert tool["inputSchema"]["properties"]["project"]["type"] == "object"


class TestToolsCall:
    async def test_score_project_returns_verdict(self, client):
        env = _envelope(
            "tools/call",
            {
                "name": SCORE_TOOL,
                "arguments": {
                    "project": {
                        "project_id": "proj_abc",
                        "title": "Demo project",
                        "files": [{"path": "index.html", "size_bytes": 200}],
                    },
                    "bounty": {
                        "title": "Best Demo",
                        "sponsor_name": "Helix Capital",
                    },
                },
            },
        )
        r = await client.post("/route", json=env)
        body = await r.json()
        assert body["error"] is None

        result = body["response"]["result"]
        # MCP protocol form: a `content` array of {type, text}.
        assert isinstance(result["content"], list)
        assert result["content"][0]["type"] == "text"
        # We also surface the parsed verdict dict for callers that do
        # not want to re-parse the text payload.
        verdict = result["structuredContent"]
        assert verdict["project_id"] == "proj_abc"
        assert verdict["judge_peer_id"] == JUDGE_PEER
        assert "scores" in verdict and len(verdict["scores"]) == 5
        # Same verdict survives a roundtrip through the text channel.
        assert json.loads(result["content"][0]["text"])["project_id"] == "proj_abc"

    async def test_unknown_tool_returns_jsonrpc_error(self, client):
        env = _envelope("tools/call", {"name": "no_such_tool", "arguments": {}})
        r = await client.post("/route", json=env)
        body = await r.json()
        assert body["error"] is None  # transport ok
        rpc = body["response"]
        assert rpc["error"]["code"] == -32601
        assert "no_such_tool" in rpc["error"]["message"]


class TestUnknownMethod:
    async def test_returns_jsonrpc_error(self, client):
        r = await client.post("/route", json=_envelope("not_a_real_method"))
        body = await r.json()
        rpc = body["response"]
        assert rpc["error"]["code"] == -32601


class TestUnknownService:
    async def test_404(self, client):
        env = _envelope("tools/list")
        env["service"] = "weather"
        r = await client.post("/route", json=env)
        assert r.status == 404


class TestHealth:
    async def test_health_endpoint(self, client):
        r = await client.get("/health")
        assert r.status == 200
        body = await r.json()
        assert body["service"] == SERVICE_NAME


class TestScoreHandlerDirect:
    """Drive `make_score_handler` without HTTP so the test stays fast."""

    def test_returns_full_verdict_shape(self):
        h = make_score_handler(JUDGE_PEER)
        verdict = h(
            {
                "project": {"project_id": "p1", "title": "T"},
                "bounty": {"title": "B", "sponsor_name": "Helix Capital"},
            }
        )
        assert verdict["project_id"] == "p1"
        assert verdict["judge_peer_id"] == JUDGE_PEER
        assert isinstance(verdict["total"], float)
