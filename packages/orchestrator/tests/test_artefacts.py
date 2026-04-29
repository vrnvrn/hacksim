"""Tests for the ArtefactStore and the static / files / register endpoints."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from packages.orchestrator import ArtefactError, ArtefactStore, CSP_HEADER, SseHub
from packages.orchestrator.api import create_app


pytestmark = pytest.mark.skipif(
    shutil.which("git") is None,
    reason="git is required for artefact archive tests",
)


@pytest.fixture
def working_dir(tmp_path: Path) -> Path:
    """Create a small git repo with two committed files. Returns the work dir."""
    work = tmp_path / "build"
    work.mkdir()
    (work / "index.html").write_text("<!doctype html><h1>Hello</h1>", encoding="utf-8")
    (work / "style.css").write_text("body { background: red; }", encoding="utf-8")

    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=work, check=True)
    subprocess.run(["git", "config", "user.email", "x@y.z"], cwd=work, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=work, check=True)
    subprocess.run(["git", "add", "-A"], cwd=work, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=work, check=True)
    return work


@pytest.fixture
def store(tmp_path: Path) -> ArtefactStore:
    return ArtefactStore(base_dir=tmp_path / "sim-runs")


def _commit_hash(work: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=work,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


class TestStoreRegister:
    def test_archives_files_to_sim_runs(self, store, working_dir):
        record = store.register(
            "sim_a",
            {
                "project_id": "proj_x",
                "working_dir": str(working_dir),
                "commit_hash": _commit_hash(working_dir),
                "entry_path": "index.html",
                "title": "Demo",
                "tagline": "A demo.",
            },
        )
        assert (record.base_dir / "index.html").exists()
        assert (record.base_dir / "style.css").exists()
        assert record.title == "Demo"
        assert record.entry_path == "index.html"

    def test_files_metadata(self, store, working_dir):
        record = store.register(
            "sim_a",
            {
                "project_id": "proj_x",
                "working_dir": str(working_dir),
                "commit_hash": _commit_hash(working_dir),
                "entry_path": "index.html",
            },
        )
        files = record.files()
        names = {f["path"] for f in files}
        assert names == {"index.html", "style.css"}
        for f in files:
            assert f["size_bytes"] > 0
            assert f["kind"] in {"text", "image", "binary"}

    def test_get_returns_registered_record(self, store, working_dir):
        store.register(
            "sim_a",
            {
                "project_id": "proj_x",
                "working_dir": str(working_dir),
                "commit_hash": _commit_hash(working_dir),
                "entry_path": "index.html",
            },
        )
        rec = store.get("sim_a", "proj_x")
        assert rec is not None
        assert rec.project_id == "proj_x"

    def test_re_register_overwrites(self, store, working_dir):
        store.register(
            "sim_a",
            {
                "project_id": "proj_x",
                "working_dir": str(working_dir),
                "commit_hash": _commit_hash(working_dir),
                "entry_path": "index.html",
            },
        )
        # Add a new file and recommit, re-register; old missing file should be gone.
        (working_dir / "new.txt").write_text("hello", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=working_dir, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "two"], cwd=working_dir, check=True)
        record = store.register(
            "sim_a",
            {
                "project_id": "proj_x",
                "working_dir": str(working_dir),
                "commit_hash": _commit_hash(working_dir),
                "entry_path": "index.html",
            },
        )
        assert (record.base_dir / "new.txt").exists()
        assert (record.base_dir / "index.html").exists()

    def test_missing_field_raises(self, store):
        with pytest.raises(ArtefactError, match="missing field"):
            store.register("sim_a", {"project_id": "p"})

    def test_missing_working_dir_raises(self, store):
        with pytest.raises(ArtefactError, match="working_dir"):
            store.register(
                "sim_a",
                {
                    "project_id": "p",
                    "working_dir": "/does/not/exist",
                    "commit_hash": "deadbeef",
                    "entry_path": "x.html",
                },
            )


class TestSafePath:
    def test_resolves_in_bounds(self, store, working_dir):
        store.register(
            "sim_a",
            {
                "project_id": "proj_x",
                "working_dir": str(working_dir),
                "commit_hash": _commit_hash(working_dir),
                "entry_path": "index.html",
            },
        )
        path = store.safe_path("sim_a", "proj_x", "index.html")
        assert path is not None
        assert path.name == "index.html"

    def test_rejects_traversal(self, store, working_dir):
        store.register(
            "sim_a",
            {
                "project_id": "proj_x",
                "working_dir": str(working_dir),
                "commit_hash": _commit_hash(working_dir),
                "entry_path": "index.html",
            },
        )
        for evil in ["../etc/passwd", "subdir/../../escape", "/etc/passwd"]:
            assert store.safe_path("sim_a", "proj_x", evil) is None

    def test_unknown_project_returns_none(self, store):
        assert store.safe_path("sim_a", "ghost", "x") is None


class TestApiRoutes:
    def test_register_project_archives_and_publishes(self, tmp_path, working_dir):
        hub = SseHub(capacity=64)
        store = ArtefactStore(base_dir=tmp_path / "sim-runs")
        app = create_app(hub=hub, artefacts=store)
        client = TestClient(app)

        sim_id = client.post("/api/sim", json={"prompt": "x"}).json()["id"]
        resp = client.post(
            f"/api/sim/{sim_id}/projects",
            json={
                "project_id": "proj_x",
                "team_id": "team_x",
                "bounty_id": "bnt_1",
                "title": "Demo",
                "tagline": "A demo.",
                "working_dir": str(working_dir),
                "commit_hash": _commit_hash(working_dir),
                "entry_path": "index.html",
            },
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["project_id"] == "proj_x"
        assert body["entry_path"] == "index.html"
        assert any(f["path"] == "index.html" for f in body["files"])

        # The hub should have at least two events: sim.created plus project.submitted.
        assert hub.buffer_len(sim_id) >= 2

    def test_files_endpoint(self, tmp_path, working_dir):
        hub = SseHub(capacity=64)
        store = ArtefactStore(base_dir=tmp_path / "sim-runs")
        app = create_app(hub=hub, artefacts=store)
        client = TestClient(app)

        sim_id = client.post("/api/sim", json={"prompt": "x"}).json()["id"]
        client.post(
            f"/api/sim/{sim_id}/projects",
            json={
                "project_id": "proj_x",
                "working_dir": str(working_dir),
                "commit_hash": _commit_hash(working_dir),
                "entry_path": "index.html",
            },
        )
        resp = client.get(f"/api/sim/{sim_id}/projects/proj_x/files")
        assert resp.status_code == 200
        data = resp.json()
        assert data["project_id"] == "proj_x"
        assert any(f["path"] == "style.css" for f in data["files"])

    def test_files_404_for_unknown(self, tmp_path):
        store = ArtefactStore(base_dir=tmp_path / "sim-runs")
        app = create_app(hub=SseHub(), artefacts=store)
        client = TestClient(app)
        resp = client.get("/api/sim/sim_a/projects/ghost/files")
        assert resp.status_code == 404

    def test_static_serves_with_csp(self, tmp_path, working_dir):
        store = ArtefactStore(base_dir=tmp_path / "sim-runs")
        app = create_app(hub=SseHub(), artefacts=store)
        client = TestClient(app)
        sim_id = client.post("/api/sim", json={"prompt": "x"}).json()["id"]
        client.post(
            f"/api/sim/{sim_id}/projects",
            json={
                "project_id": "proj_x",
                "working_dir": str(working_dir),
                "commit_hash": _commit_hash(working_dir),
                "entry_path": "index.html",
            },
        )
        resp = client.get(f"/api/sim/{sim_id}/projects/proj_x/static/index.html")
        assert resp.status_code == 200
        assert "<h1>Hello</h1>" in resp.text
        assert resp.headers.get("content-security-policy") == CSP_HEADER
        assert resp.headers.get("x-content-type-options") == "nosniff"

    def test_static_rejects_traversal(self, tmp_path, working_dir):
        store = ArtefactStore(base_dir=tmp_path / "sim-runs")
        app = create_app(hub=SseHub(), artefacts=store)
        client = TestClient(app)
        sim_id = client.post("/api/sim", json={"prompt": "x"}).json()["id"]
        client.post(
            f"/api/sim/{sim_id}/projects",
            json={
                "project_id": "proj_x",
                "working_dir": str(working_dir),
                "commit_hash": _commit_hash(working_dir),
                "entry_path": "index.html",
            },
        )
        resp = client.get(f"/api/sim/{sim_id}/projects/proj_x/static/../../../etc/passwd")
        assert resp.status_code == 404

    def test_register_payload_missing_field_400(self, tmp_path):
        app = create_app(hub=SseHub(), artefacts=ArtefactStore(base_dir=tmp_path / "x"))
        client = TestClient(app)
        sim_id = client.post("/api/sim", json={"prompt": "x"}).json()["id"]
        resp = client.post(
            f"/api/sim/{sim_id}/projects",
            json={"project_id": "p"},  # missing working_dir, commit_hash, entry_path
        )
        assert resp.status_code == 400
