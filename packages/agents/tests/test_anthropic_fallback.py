"""End-to-end test of the Anthropic fallback path across every decision site.

When the Anthropic SDK raises (network down, 401, 429, malformed JSON,
truncated response), each decision module must:

1. Emit one `decision.anthropic_failed` event with the operation name and
   the error class so a judge looking at the SSE stream knows the SDK
   was attempted and why it fell back.
2. Fall through to the deterministic stub so the run still produces a
   real artefact.

The test installs a fake `anthropic` module and `anthropic.Anthropic` so we
exercise the helper plumbing without a live SDK install.
"""

from __future__ import annotations

import sys
import types
from typing import Any

import pytest


@pytest.fixture(autouse=True)
def _api_key_set(monkeypatch):
    """All four decision sites only attempt the SDK call when the env var
    is set, so the test sets a placeholder and swaps the SDK module."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake-key")


def _install_fake_anthropic(monkeypatch, *, raise_class: str = "APIConnectionError"):
    """Install a stub `anthropic` module that raises a named SDK error.

    `_anthropic.call_with_retry` switches on the exception's class name to
    decide whether to retry. We model both the retryable and the fatal
    cases by parameterising `raise_class`.
    """

    class _FakeError(Exception):
        status_code: int | None = 503

        def __init__(self, message: str = "fake transport error"):
            super().__init__(message)

    _FakeError.__name__ = raise_class

    class _FakeClient:
        def __init__(self, *_, **__):
            pass

        @property
        def messages(self):
            return self

        def create(self, **_kwargs):
            raise _FakeError()

    fake_mod = types.SimpleNamespace(Anthropic=_FakeClient)
    monkeypatch.setitem(sys.modules, "anthropic", fake_mod)
    return _FakeClient


class _Recorder:
    """Tiny `state.emit` stand-in that captures every emitted event."""

    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    def __call__(self, event_type: str, payload: dict[str, Any]) -> None:
        self.events.append((event_type, payload))


def _failure_event(rec: _Recorder, operation: str) -> dict[str, Any]:
    """Return the single decision.anthropic_failed event for `operation`."""
    matches = [
        p
        for t, p in rec.events
        if t == "decision.anthropic_failed" and p.get("operation") == operation
    ]
    assert len(matches) == 1, (
        f"expected exactly one decision.anthropic_failed for {operation}, "
        f"got {len(matches)}: {rec.events}"
    )
    return matches[0]


class TestProposeBountyFallback:
    def test_falls_back_to_stub_on_sdk_failure(self, monkeypatch):
        from packages.agents.bounty_designer.decisions import propose_bounty

        _install_fake_anthropic(monkeypatch)
        rec = _Recorder()

        peer = "f" * 64
        result = propose_bounty(sim_prompt="protein folding", sender_peer_id=peer, emit=rec)

        for key in ("title", "sponsor_name", "prize_amount_usd", "description", "qualification"):
            assert key in result, f"stub fallback missing required field {key}"

        evt = _failure_event(rec, "propose_bounty")
        assert evt["error_class"] == "APIConnectionError"
        assert evt["attempts"] == 2  # retried once on a transient class

    def test_non_retryable_class_records_one_attempt(self, monkeypatch):
        from packages.agents.bounty_designer.decisions import propose_bounty

        _install_fake_anthropic(monkeypatch, raise_class="AuthenticationError")
        rec = _Recorder()
        propose_bounty(sim_prompt="anything", sender_peer_id="a" * 64, emit=rec)

        evt = _failure_event(rec, "propose_bounty")
        assert evt["error_class"] == "AuthenticationError"
        assert evt["attempts"] == 1


class TestPickBountyFallback:
    def test_falls_back_to_scoring(self, monkeypatch):
        from packages.agents.builder.decisions import pick_bounty

        _install_fake_anthropic(monkeypatch, raise_class="APITimeoutError")
        rec = _Recorder()

        bounties = [
            {"id": "bnt_zk", "title": "ZK", "description": "ZK proofs", "qualification": []},
            {"id": "bnt_bio", "title": "Bio", "description": "biology", "qualification": []},
        ]
        chosen = pick_bounty(bounties=bounties, skills=["ZK"], emit=rec)
        assert chosen is bounties[0]
        evt = _failure_event(rec, "pick_bounty")
        assert evt["error_class"] == "APITimeoutError"
        assert evt["attempts"] == 2


class TestWriteProjectFallback:
    def test_falls_back_to_stub_html(self, monkeypatch, tmp_path):
        import shutil

        if shutil.which("git") is None:
            pytest.skip("git not on PATH")

        from packages.agents.builder.build import write_project

        _install_fake_anthropic(monkeypatch)
        rec = _Recorder()

        bounty = {
            "id": "bnt_1",
            "title": "Best Visualisation Tool",
            "sponsor_name": "FoldLab",
            "description": "Build something a layman can play with.",
            "qualification": ["uses real data"],
        }
        result = write_project(
            work_dir=tmp_path / "proj",
            bounty=bounty,
            skills=["Python"],
            sender_peer_id="c" * 64,
            sim_prompt="research hackathon",
            emit=rec,
        )

        # Stub fallback wrote the canonical three-file project.
        assert (tmp_path / "proj" / "index.html").exists()
        assert (tmp_path / "proj" / "style.css").exists()
        assert (tmp_path / "proj" / "app.js").exists()
        assert isinstance(result["commit_hash"], str) and len(result["commit_hash"]) >= 7

        evt = _failure_event(rec, "compose_project")
        assert evt["error_class"] == "APIConnectionError"


class TestScoreProjectFallback:
    def test_falls_back_to_archetype_stub(self, monkeypatch):
        from packages.agents.judge.decisions import score_project
        from packages.agents.judge.persona import CRITERIA

        _install_fake_anthropic(monkeypatch)
        rec = _Recorder()

        verdict = score_project(
            project={"project_id": "p1", "title": "P", "files": []},
            bounty={"title": "Bounty", "sponsor_name": "Helix Capital"},
            judge_peer_id="d" * 64,
            emit=rec,
        )
        # Stub returns a verdict with all five criteria scored.
        assert set(verdict["scores"].keys()) == set(CRITERIA)
        assert isinstance(verdict["total"], float)
        assert isinstance(verdict["feedback"], str) and verdict["feedback"]

        evt = _failure_event(rec, "score_project")
        assert evt["error_class"] == "APIConnectionError"


class TestEmitNoneIsSafe:
    """Decision modules accept emit=None for callers that do not want SSE
    coupling (tests, smoke harness inserts). Failures must still fall back."""

    def test_propose_bounty_no_emit(self, monkeypatch):
        from packages.agents.bounty_designer.decisions import propose_bounty

        _install_fake_anthropic(monkeypatch)
        result = propose_bounty(sim_prompt="x", sender_peer_id="e" * 64)
        assert "title" in result

    def test_score_project_no_emit(self, monkeypatch):
        from packages.agents.judge.decisions import score_project

        _install_fake_anthropic(monkeypatch)
        verdict = score_project(
            project={"project_id": "p"},
            bounty={"title": "B"},
            judge_peer_id="f" * 64,
        )
        assert "scores" in verdict
