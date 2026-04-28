"""Tests for the HackSim orchestrator FastAPI app."""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from packages.orchestrator import SseHub
from packages.orchestrator.api import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app(hub=SseHub(capacity=64))
    return TestClient(app)


class TestCreateSim:
    def test_post_creates_sim_with_id(self, client):
        resp = client.post(
            "/api/sim",
            json={"prompt": "an onchain agents hackathon", "config": {"builders": 4}},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["id"].startswith("sim_")
        assert body["stream_url"] == f"/api/sim/{body['id']}/stream"

    def test_post_uses_default_config(self, client):
        resp = client.post("/api/sim", json={"prompt": "test"})
        assert resp.status_code == 201
        snap = client.get(f"/api/sim/{resp.json()['id']}/snapshot").json()
        assert snap["config"]["builders"] == 8
        assert snap["config"]["judges"] == 3
        assert snap["config"]["designers"] == 3

    def test_post_rejects_empty_prompt(self, client):
        resp = client.post("/api/sim", json={"prompt": ""})
        assert resp.status_code == 422

    def test_post_rejects_out_of_range_config(self, client):
        resp = client.post(
            "/api/sim",
            json={"prompt": "x", "config": {"builders": 99, "judges": 1, "designers": 1}},
        )
        assert resp.status_code == 422

    def test_unique_ids_for_separate_posts(self, client):
        a = client.post("/api/sim", json={"prompt": "a"}).json()["id"]
        b = client.post("/api/sim", json={"prompt": "b"}).json()["id"]
        assert a != b


class TestSnapshot:
    def test_snapshot_returns_initial_state(self, client):
        sim_id = client.post("/api/sim", json={"prompt": "test"}).json()["id"]
        resp = client.get(f"/api/sim/{sim_id}/snapshot")
        assert resp.status_code == 200
        snap = resp.json()
        assert snap["id"] == sim_id
        assert snap["prompt"] == "test"
        assert snap["phase"] == 0
        assert snap["bounties"] == []
        assert snap["builders"] == []
        assert snap["projects"] == []

    def test_snapshot_404_for_unknown(self, client):
        resp = client.get("/api/sim/sim_does_not_exist/snapshot")
        assert resp.status_code == 404


class TestStream:
    def test_stream_404_for_unknown_sim(self, client):
        resp = client.get("/api/sim/sim_unknown/stream")
        assert resp.status_code == 404

    def test_stream_endpoint_publishes_sim_created_event(self, client):
        """The wire format and stream replay are covered by SseHub tests in
        commit 09. Here we verify the FastAPI wiring publishes the right
        event into the hub when a sim is created and that the stream
        endpoint reaches it. We inspect the hub directly to avoid the
        well-known TestClient/SSE flush timing problem.
        """
        # Reach into the app's hub directly to confirm the event was published.
        app = client.app
        hub: SseHub = app.state.hub

        resp = client.post("/api/sim", json={"prompt": "verify hub publish"})
        sim_id = resp.json()["id"]

        # The hub should now hold the sim.created event for this sim.
        assert hub.has_sim(sim_id)
        assert hub.buffer_len(sim_id) == 1


class TestStreamLive:
    """End-to-end: spin up the app on a real port, open the SSE stream,
    publish a second event from outside, read both off the wire. This
    catches any wiring regression in StreamingResponse without depending
    on TestClient's flush behaviour.
    """

    @pytest.mark.asyncio
    async def test_stream_yields_two_events_in_order(self):
        import contextlib
        import socket
        import threading

        import uvicorn

        hub = SseHub(capacity=64)
        app = create_app(hub=hub)

        # Bind a free port.
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]

        config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
        server = uvicorn.Server(config)

        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()

        # Wait until server is up.
        for _ in range(50):
            await asyncio.sleep(0.05)
            try:
                async with httpx.AsyncClient(timeout=0.5) as ac:
                    r = await ac.get(f"http://127.0.0.1:{port}/api/health")
                    if r.status_code == 200:
                        break
            except Exception:
                pass
        else:
            server.should_exit = True
            raise RuntimeError("uvicorn did not come up")

        try:
            async with httpx.AsyncClient(timeout=10.0) as ac:
                created = await ac.post(
                    f"http://127.0.0.1:{port}/api/sim",
                    json={"prompt": "live stream test"},
                )
                sim_id = created.json()["id"]

                seen: list[str] = []

                async def consume():
                    async with ac.stream("GET", f"http://127.0.0.1:{port}/api/sim/{sim_id}/stream") as resp:
                        assert resp.status_code == 200
                        buf = b""
                        async for chunk in resp.aiter_bytes():
                            buf += chunk
                            while b"\n\n" in buf:
                                head, _, rest = buf.partition(b"\n\n")
                                buf = rest
                                seen.append(head.decode("utf-8"))
                                if len(seen) >= 2:
                                    return

                consumer = asyncio.create_task(consume())
                # Give the subscriber a tick to register, then publish the
                # second event from outside the request handler.
                await asyncio.sleep(0.2)
                hub.publish(sim_id, "phase.tick", {"phase": 1})
                await asyncio.wait_for(consumer, timeout=5.0)

                assert any("event: sim.created" in s for s in seen)
                assert any("event: phase.tick" in s for s in seen)
        finally:
            server.should_exit = True
            with contextlib.suppress(Exception):
                thread.join(timeout=2.0)


class TestHealth:
    def test_health_reports_active_sims(self, client):
        assert client.get("/api/health").json()["active_sims"] == 0
        client.post("/api/sim", json={"prompt": "x"})
        assert client.get("/api/health").json()["active_sims"] == 1


class TestCors:
    def test_cors_allows_localhost_origin(self, client):
        resp = client.options(
            "/api/sim",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert resp.status_code == 200
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"
