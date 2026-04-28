"""Tests for the project build pipeline."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from packages.agents.builder.build import _compose_stub, write_project


PEER_A = "a" * 64
PEER_B = "b" * 64


@pytest.fixture(autouse=True)
def _no_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


@pytest.fixture
def bounty():
    return {
        "id": "bnt_1",
        "title": "Best Visualisation Tool",
        "sponsor_name": "FoldLab",
        "description": "Build a visualisation that helps a layman understand a hard subject.",
        "qualification": ["uses real data", "works in a sandboxed iframe"],
    }


class TestComposeStub:
    def test_includes_required_files(self, bounty):
        files = _compose_stub(bounty=bounty, skills=["Python"], sender_peer_id=PEER_A)
        assert "index.html" in files
        assert "style.css" in files
        assert "app.js" in files
        assert "__title" in files
        assert "__tagline" in files

    def test_html_references_companion_files(self, bounty):
        files = _compose_stub(bounty=bounty, skills=["Python"], sender_peer_id=PEER_A)
        html = files["index.html"]
        assert 'href="style.css"' in html
        assert 'src="app.js"' in html

    def test_html_includes_bounty_title_and_sponsor(self, bounty):
        files = _compose_stub(bounty=bounty, skills=["Python"], sender_peer_id=PEER_A)
        html = files["index.html"]
        assert "Best Visualisation Tool" in html
        assert "FoldLab" in html

    def test_html_includes_skills_as_pills(self, bounty):
        files = _compose_stub(
            bounty=bounty, skills=["Python", "viz", "ML"], sender_peer_id=PEER_A
        )
        html = files["index.html"]
        for skill in ["Python", "viz", "ML"]:
            assert skill in html

    def test_html_no_external_network_calls(self, bounty):
        files = _compose_stub(bounty=bounty, skills=["Python"], sender_peer_id=PEER_A)
        html = files["index.html"]
        # No CDN scripts, no external stylesheets, no API calls.
        for needle in ["cdnjs", "https://", "http://", "fetch(", "XMLHttpRequest"]:
            assert needle not in html, f"forbidden token '{needle}' in index.html"

    def test_two_peers_get_visibly_different_styles(self, bounty):
        a = _compose_stub(bounty=bounty, skills=["Python"], sender_peer_id=PEER_A)
        b = _compose_stub(bounty=bounty, skills=["Python"], sender_peer_id=PEER_B)
        # The accent hue lives in style.css; different peer ids -> different css.
        assert a["style.css"] != b["style.css"]


class TestWriteProject:
    def test_creates_files_and_commits(self, tmp_path, bounty):
        if shutil.which("git") is None:
            pytest.skip("git not on PATH")
        result = write_project(
            work_dir=tmp_path / "proj",
            bounty=bounty,
            skills=["Python", "viz"],
            sender_peer_id=PEER_A,
            sim_prompt="research hackathon",
        )
        assert (tmp_path / "proj" / "index.html").exists()
        assert (tmp_path / "proj" / "style.css").exists()
        assert (tmp_path / "proj" / "app.js").exists()
        assert (tmp_path / "proj" / ".git").exists()
        assert isinstance(result["commit_hash"], str)
        assert len(result["commit_hash"]) >= 7
        assert result["entry_path"] == "index.html"
        assert any(f["path"] == "index.html" for f in result["files"])

    def test_commit_hash_resolves_in_repo(self, tmp_path, bounty):
        if shutil.which("git") is None:
            pytest.skip("git not on PATH")
        result = write_project(
            work_dir=tmp_path / "proj",
            bounty=bounty,
            skills=["Python"],
            sender_peer_id=PEER_A,
        )
        rev = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=tmp_path / "proj",
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        assert rev.startswith(result["commit_hash"])

    def test_files_metadata_has_size(self, tmp_path, bounty):
        if shutil.which("git") is None:
            pytest.skip("git not on PATH")
        result = write_project(
            work_dir=tmp_path / "proj",
            bounty=bounty,
            skills=["Python"],
            sender_peer_id=PEER_A,
        )
        for f in result["files"]:
            assert f["size_bytes"] > 0
            assert f["kind"] == "text"
