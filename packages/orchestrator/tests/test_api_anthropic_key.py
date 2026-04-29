"""Tests for the Anthropic key plumbing on POST /api/sim.

Three guarantees the test pins down:

1. The key is accepted from a localhost request, plumbed into the
   spawned worker env via SimController.extra_env, and never appears
   in the SSE buffer or the snapshot.
2. The endpoint refuses the key when the request did not come from
   localhost.
3. The key is never serialised into any model_dump or repr the app
   itself emits.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from packages.orchestrator import SimController, SseHub
from packages.orchestrator.api import create_app, CreateSimRequest


SECRET = "sk-ant-api03-fake-test-key-do-not-use-do-not-log-XXXX"


def _app(tmp_path: Path):
    return create_app(
        hub=SseHub(capacity=128),
        auto_start=True,
        base_dir=tmp_path,
        axl_bin=tmp_path / "fake_axl",
        orch_url="http://127.0.0.1:8000",
    )


class TestKeyAcceptedOnLocalhost:
    def test_passed_to_controller_extra_env(self, tmp_path):
        captured: dict = {}

        original_init = SimController.__init__

        def capture_init(self, *args, **kwargs):
            captured["extra_env"] = kwargs.get("extra_env")
            original_init(self, *args, **kwargs)

        with patch(
            "packages.orchestrator.api.SimController.__init__",
            new=capture_init,
        ), patch(
            "packages.orchestrator.api.SimController.start",
            new=AsyncMock(return_value=None),
        ):
            app = _app(tmp_path)
            with TestClient(app) as client:
                resp = client.post(
                    "/api/sim",
                    json={
                        "prompt": "test",
                        "anthropic_api_key": SECRET,
                    },
                )
                assert resp.status_code == 201, resp.text
        assert captured["extra_env"] == {"ANTHROPIC_API_KEY": SECRET}


class TestKeyRefusedOffLocalhost:
    def test_rejected_with_403(self, tmp_path):
        with patch(
            "packages.orchestrator.api.SimController.start",
            new=AsyncMock(return_value=None),
        ):
            app = _app(tmp_path)
            with TestClient(app) as client:
                resp = client.post(
                    "/api/sim",
                    json={"prompt": "x", "anthropic_api_key": SECRET},
                    headers={"X-Forwarded-For": "203.0.113.42"},
                )
                # TestClient connects from 127.0.0.1 by default, but the
                # X-Forwarded-For header overrides our localhost check.
                assert resp.status_code == 403
                assert "localhost" in resp.json()["detail"].lower()


class TestKeyNeverLeaks:
    def test_key_not_in_sim_created_event(self, tmp_path):
        with patch(
            "packages.orchestrator.api.SimController.start",
            new=AsyncMock(return_value=None),
        ):
            app = _app(tmp_path)
            with TestClient(app) as client:
                resp = client.post(
                    "/api/sim",
                    json={"prompt": "test", "anthropic_api_key": SECRET},
                )
                sim_id = resp.json()["id"]
                hub: SseHub = app.state.hub
                # Walk every buffered event and assert the key string
                # never appears in any payload.
                channel = hub._channels[sim_id]  # type: ignore[attr-defined]
                for evt in channel.buffer:
                    payload_repr = repr(evt.data)
                    assert SECRET not in payload_repr
                    assert "sk-ant-" not in payload_repr

    def test_key_not_in_snapshot(self, tmp_path):
        with patch(
            "packages.orchestrator.api.SimController.start",
            new=AsyncMock(return_value=None),
        ):
            app = _app(tmp_path)
            with TestClient(app) as client:
                sim_id = client.post(
                    "/api/sim",
                    json={"prompt": "test", "anthropic_api_key": SECRET},
                ).json()["id"]
                snap = client.get(f"/api/sim/{sim_id}/snapshot").json()
                # Snapshot dump should not contain the key in any field.
                snap_repr = repr(snap)
                assert SECRET not in snap_repr
                assert "sk-ant-" not in snap_repr

    def test_key_not_in_request_repr(self):
        # Pydantic SecretStr keeps the value out of repr and model_dump.
        req = CreateSimRequest(prompt="x", anthropic_api_key=SECRET)
        assert SECRET not in repr(req)
        dumped = req.model_dump()
        assert SECRET not in repr(dumped)


class TestNoKeyStillWorks:
    def test_omitted_field_no_effect(self, tmp_path):
        with patch(
            "packages.orchestrator.api.SimController.start",
            new=AsyncMock(return_value=None),
        ):
            app = _app(tmp_path)
            with TestClient(app) as client:
                resp = client.post("/api/sim", json={"prompt": "x"})
                assert resp.status_code == 201
                sim_id = resp.json()["id"]
                # sim.created event still publishes, with `llm` set to stub.
                hub = app.state.hub
                channel = hub._channels[sim_id]  # type: ignore[attr-defined]
                created = next(
                    e for e in channel.buffer if e.type == "sim.created"
                )
                assert created.data["llm"] == "stub"
