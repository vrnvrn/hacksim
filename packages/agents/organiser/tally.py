"""Verdict tally helpers, separated so they can be unit-tested in
isolation without spinning up a worker loop.
"""

from __future__ import annotations

from typing import Any


def tally_leaderboard(
    *,
    projects: dict[str, dict[str, Any]],
    verdicts_by_project: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Compute the ranked leaderboard from accumulated state.

    `projects[pid]` is the project.submitted payload.
    `verdicts_by_project[pid]` is a list of verdict.published payloads.

    Returns a list of leaderboard entries sorted by total_score
    descending, ties broken by lower project_id alphabetically.
    """
    rows: list[dict[str, Any]] = []
    for pid, project in projects.items():
        verdicts = verdicts_by_project.get(pid, [])
        if verdicts:
            total_avg = sum(v.get("total", 0.0) for v in verdicts) / len(verdicts)
            scored_count = len(verdicts)
        else:
            total_avg = 0.0
            scored_count = 0
        rows.append(
            {
                "project_id": pid,
                "title": project.get("title", "Untitled"),
                "team_id": project.get("team_id"),
                "bounty_id": project.get("bounty_id"),
                "total_score": round(total_avg, 2),
                "verdicts": scored_count,
            }
        )
    rows.sort(key=lambda r: (-r["total_score"], r["project_id"]))
    for i, row in enumerate(rows):
        row["rank"] = i + 1
    return rows
