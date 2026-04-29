"""Snapshot accumulator.

A pure function that translates a stream of HackSim events into the
Snapshot shape the frontend consumes. Each event type maps to a
mutation of the snapshot's bounties / builders / teams / projects /
judges / verdicts arrays, plus the phase counter.

Used by the SimController to maintain `sim.snapshot` as events flow
through the SseHub. Tested in isolation here; SimController bolts the
side-effects on top.

Wire-side envelope payloads land verbatim in the snapshot rows where
fields match `lib/types.ts` (UX_SPEC.md section 7). Worker-internal
events ("designer.composing", "builder.heard_bounty", etc.) flow
through to the SSE feed but do not mutate the snapshot.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from packages.protocol import Phase


def _empty_snapshot(*, sim_id: str, prompt: str, config: dict, created_at: str) -> dict:
    return {
        "id": sim_id,
        "prompt": prompt,
        "config": config,
        "phase": 0,
        "created_at": created_at,
        "bounties": [],
        "builders": [],
        "teams": [],
        "projects": [],
        "judges": [],
        "verdicts": [],
    }


def apply_event(snapshot: dict, event_type: str, payload: dict) -> dict:
    """Return a new snapshot with `event_type` applied. Pure: caller owns the
    new dict. Unknown events return the snapshot unchanged so the run log
    catches them but the state stays consistent.
    """
    new = deepcopy(snapshot)

    if event_type == "phase.tick":
        try:
            new["phase"] = int(payload.get("phase", new["phase"]))
        except (TypeError, ValueError):
            pass
        return new

    if event_type == "bounty.posted":
        bid = str(payload.get("id") or payload.get("bounty_id") or "")
        if not bid or any(b["id"] == bid for b in new["bounties"]):
            return new
        new["bounties"].append(
            {
                "id": bid,
                "title": str(payload.get("title", "Untitled")),
                "sponsor_name": str(payload.get("sponsor_name", "")),
                "sponsor_peer_id": str(payload.get("sponsor_peer_id", "")),
                "prize_amount_usd": int(payload.get("prize_amount_usd", 0)),
                "description": str(payload.get("description", "")),
                "qualification": list(payload.get("qualification", []) or []),
                "created_at": str(payload.get("created_at", "")),
            }
        )
        return new

    if event_type == "team.formed":
        tid = str(payload.get("id") or payload.get("team_id") or "")
        if not tid or any(t["id"] == tid for t in new["teams"]):
            return new
        members = list(payload.get("members", []) or [])
        new["teams"].append(
            {
                "id": tid,
                "bounty_id": str(payload.get("bounty_id", "")),
                "members": members,
                "formed_at": str(payload.get("formed_at", "")),
            }
        )
        # Reflect the team membership on the builder row if it exists.
        for member_peer in members:
            for b in new["builders"]:
                if b["peer_id"] == member_peer:
                    b["team_id"] = tid
                    b["current_bounty_id"] = str(payload.get("bounty_id", "")) or None
        return new

    if event_type == "project.submitted":
        pid = str(payload.get("project_id") or payload.get("id") or "")
        if not pid or any(p["id"] == pid for p in new["projects"]):
            return new
        new["projects"].append(
            {
                "id": pid,
                "team_id": str(payload.get("team_id", "")),
                "bounty_id": str(payload.get("bounty_id", "")),
                "title": str(payload.get("title", "Untitled")),
                "tagline": str(payload.get("tagline", "")),
                "description": str(payload.get("description", "")),
                "status": "submitted",
                "submitted_at": str(payload.get("submitted_at", "")),
                "commit_hash": str(payload.get("commit_hash", "")) or None,
                "entry_path": str(payload.get("entry_path", "")) or None,
                "artefact_path": "served",
                "github_url": payload.get("github_url"),
            }
        )
        return new

    if event_type == "rubric.published":
        judge_pk = str(payload.get("judge_peer_id") or payload.get("sender_id") or "")
        if not judge_pk:
            return new
        rubric = list(payload.get("rubric", []) or [])
        existing = next((j for j in new["judges"] if j["peer_id"] == judge_pk), None)
        if existing is None:
            new["judges"].append(
                {
                    "peer_id": judge_pk,
                    "display_name": str(payload.get("judge_name", f"J-{judge_pk[:4]}")),
                    "rubric": rubric,
                    "scored_count": 0,
                    "total_to_score": len(new["projects"]),
                }
            )
        else:
            existing["rubric"] = rubric
        return new

    if event_type == "verdict.published":
        pid = str(payload.get("project_id", ""))
        judge_pk = str(payload.get("judge_peer_id", ""))
        if not pid or not judge_pk:
            return new
        verdict_id = f"{pid}:{judge_pk}"
        if any(
            v.get("project_id") == pid and v.get("judge_peer_id") == judge_pk
            for v in new["verdicts"]
        ):
            return new
        new["verdicts"].append(
            {
                "id": verdict_id,
                "project_id": pid,
                "judge_peer_id": judge_pk,
                "scores": dict(payload.get("scores", {}) or {}),
                "total": float(payload.get("total", 0.0)),
                "feedback": str(payload.get("feedback", "")),
                "interactions_summary": str(payload.get("interactions_summary", "")),
            }
        )
        for j in new["judges"]:
            if j["peer_id"] == judge_pk:
                j["scored_count"] = sum(
                    1 for v in new["verdicts"] if v["judge_peer_id"] == judge_pk
                )
                j["total_to_score"] = len(new["projects"])
        # Mark the project as judged once at least one verdict exists.
        for p in new["projects"]:
            if p["id"] == pid:
                p["status"] = "judged"
        return new

    if event_type == "hackathon.closed":
        new["phase"] = Phase.SHOWCASE
        leaderboard = payload.get("leaderboard", []) or []
        new["leaderboard"] = list(leaderboard)
        return new

    if event_type == "builder.registered":
        # Internal event used by SimController to seed the builder roster
        # ahead of the first bounty.posted, so the live page shows builder
        # chips immediately.
        peer = str(payload.get("peer_id", ""))
        if not peer or any(b["peer_id"] == peer for b in new["builders"]):
            return new
        new["builders"].append(
            {
                "peer_id": peer,
                "display_name": str(payload.get("display_name", f"B-{peer[:4]}")),
                "skills": list(payload.get("skills", []) or []),
                "team_id": None,
                "current_bounty_id": None,
            }
        )
        return new

    return new


def apply_events(initial: dict, events: list[tuple[str, dict]]) -> dict:
    """Fold a sequence of (event_type, payload) pairs through apply_event."""
    snap = initial
    for event_type, payload in events:
        snap = apply_event(snap, event_type, payload)
    return snap


def empty_snapshot(*, sim_id: str, prompt: str, config: dict, created_at: str) -> dict:
    """Public helper to build a fresh snapshot for a new sim."""
    return _empty_snapshot(
        sim_id=sim_id,
        prompt=prompt,
        config=config,
        created_at=created_at,
    )
