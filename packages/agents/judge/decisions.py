"""Score a project submission against the rubric.

Two decision paths, same envelope shape. The default produces
deterministic, archetype-flavoured scores keyed off the
(judge_peer_id, project_id) pair so two judges score the same project
differently while the same judge always returns the same numbers. With
`ANTHROPIC_API_KEY` set, scoring upgrades to a Claude call against the
rubric and the bounty's qualification list.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Callable
from typing import Any

from packages.agents._anthropic import call_with_retry, get_model, make_client

from .persona import CRITERIA, archetype_for_peer_id, load_persona_text

EmitFn = Callable[[str, dict[str, Any]], None]


def score_project(
    *,
    project: dict[str, Any],
    bounty: dict[str, Any] | None,
    judge_peer_id: str,
    emit: EmitFn | None = None,
) -> dict[str, Any]:
    """Return a verdict dict for one project.

    Verdict shape (matches UX_SPEC.md section 7 `Verdict`):
        {
            "project_id": str,
            "judge_peer_id": str,
            "scores": {criterion: 0..10, ...},
            "total": float,         # 0..10, weighted by archetype
            "feedback": str,
            "interactions_summary": str,
            "archetype": str,
        }

    `emit`, when supplied, is the role worker's `state.emit` so SDK
    failures land on the SSE stream as `decision.anthropic_failed`.
    """
    if api_key := os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return _score_via_anthropic(
                project=project,
                bounty=bounty,
                judge_peer_id=judge_peer_id,
                api_key=api_key,
                emit=emit,
            )
        except Exception:
            # Failure already surfaced via `decision.anthropic_failed`;
            # fall back to the deterministic archetype-flavoured stub.
            pass
    return _score_stub(project=project, bounty=bounty, judge_peer_id=judge_peer_id)


def _score_stub(
    *,
    project: dict[str, Any],
    bounty: dict[str, Any] | None,
    judge_peer_id: str,
) -> dict[str, Any]:
    archetype = archetype_for_peer_id(judge_peer_id)
    project_id = str(project.get("project_id", ""))
    h = hashlib.sha256(f"{judge_peer_id}|{project_id}".encode()).digest()

    # Per-criterion base score 4..9 with archetype bias on each axis.
    scores: dict[str, int] = {}
    for i, crit in enumerate(CRITERIA):
        base = 4 + (h[i] % 6)  # 4..9
        bias = _archetype_bias(archetype["name"], crit)
        score = max(0, min(10, base + bias))
        scores[crit] = score

    weights = archetype["weights"]
    total = sum(scores[crit] * w for crit, w in zip(CRITERIA, weights, strict=True))
    total = round(total, 2)

    bounty_title = (bounty or {}).get("title", "the chosen bounty")
    bounty_sponsor = (bounty or {}).get("sponsor_name", "the sponsor")
    feedback = _stub_feedback(
        archetype=archetype,
        scores=scores,
        project_title=str(project.get("title", "the project")),
        bounty_title=str(bounty_title),
        sponsor=str(bounty_sponsor),
    )

    return {
        "project_id": project_id,
        "judge_peer_id": judge_peer_id,
        "scores": scores,
        "total": total,
        "feedback": feedback,
        "interactions_summary": "",
        "archetype": archetype["name"],
    }


def _archetype_bias(archetype_name: str, criterion: str) -> int:
    """Return a +/-1 bias for a given archetype on a given criterion.

    The bias nudges the base score so each archetype's verdicts feel
    distinct without overwhelming the per-project signal. Sum of all
    biases per archetype is roughly zero.
    """
    table = {
        "encouraging": {"demo_quality": +1, "documentation": +1, "technical_depth": -1, "novelty": -1},
        "balanced": {},
        "strict": {"technical_depth": +1, "novelty": +1, "demo_quality": -1, "documentation": +1},
        "contrarian": {"novelty": +2, "bounty_fit": +1, "demo_quality": -1, "documentation": -1},
    }
    return table.get(archetype_name, {}).get(criterion, 0)


def _stub_feedback(
    *,
    archetype: dict,
    scores: dict[str, int],
    project_title: str,
    bounty_title: str,
    sponsor: str,
) -> str:
    """Compose a one-paragraph feedback line in the archetype's voice."""
    high = max(scores, key=lambda k: scores[k])
    low = min(scores, key=lambda k: scores[k])
    name = archetype["name"]
    if name == "encouraging":
        return (
            f"{project_title} takes the {bounty_title} bounty in a clean direction. "
            f"The {high.replace('_', ' ')} stands out. With more attention on "
            f"{low.replace('_', ' ')} this becomes a strong submission for {sponsor}."
        )
    if name == "balanced":
        return (
            f"On the {bounty_title} bounty, {project_title} reads as a measured attempt. "
            f"Strongest on {high.replace('_', ' ')}, weakest on {low.replace('_', ' ')}. "
            f"A solid mid-pack contender for {sponsor}."
        )
    if name == "strict":
        return (
            f"{project_title} answers the {bounty_title} brief with mixed depth. "
            f"The {high.replace('_', ' ')} carries it; the {low.replace('_', ' ')} is "
            f"thin enough that {sponsor} would want a v2 before shipping."
        )
    if name == "contrarian":
        return (
            f"{project_title} chooses an angle on {bounty_title} most teams would skip. "
            f"That earned it on {high.replace('_', ' ')}. The {low.replace('_', ' ')} is "
            f"weak, but {sponsor} should reward the unusual read."
        )
    return f"{project_title} scored across the rubric without a strong outlier."


_VERDICT_REQUIRED = {"scores", "total", "feedback"}


def _score_via_anthropic(
    *,
    project: dict[str, Any],
    bounty: dict[str, Any] | None,
    judge_peer_id: str,
    api_key: str,
    emit: EmitFn | None = None,
) -> dict[str, Any]:
    """Ask Claude to score the project against the rubric. Validates JSON."""
    archetype = archetype_for_peer_id(judge_peer_id)
    rubric = dict(zip(CRITERIA, archetype["weights"], strict=True))

    user_prompt = (
        f"Your archetype is {archetype['name']}, {archetype['tone_hint']}.\n"
        f"Rubric weights (sum to 1): {json.dumps(rubric)}\n\n"
        f"Bounty: {json.dumps(bounty or {}, indent=2)}\n\n"
        f"Project:\n{json.dumps({k: project.get(k) for k in ['title', 'tagline', 'commit_hash', 'entry_path', 'files']}, indent=2)}\n\n"
        "Score each criterion 0 to 10 (integer), compute the weighted total "
        "(round to 2 decimals), and write one paragraph of feedback. "
        "Respond with JSON only, with keys 'scores' (object of criterion to "
        "integer), 'total' (number), and 'feedback' (string)."
    )

    client = make_client(api_key)
    response = call_with_retry(
        lambda: client.messages.create(
            model=get_model(),
            max_tokens=512,
            system=load_persona_text(),
            messages=[{"role": "user", "content": user_prompt}],
        ),
        operation="score_project",
        emit=emit,
    )
    text = "".join(block.text for block in response.content if hasattr(block, "text")).strip()
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("no JSON in response")
    obj = json.loads(match.group(0))
    missing = _VERDICT_REQUIRED - obj.keys()
    if missing:
        raise ValueError(f"verdict missing fields: {sorted(missing)}")

    scores = {k: int(v) for k, v in obj["scores"].items() if k in CRITERIA}
    for crit in CRITERIA:
        scores.setdefault(crit, 5)
        scores[crit] = max(0, min(10, scores[crit]))

    return {
        "project_id": str(project.get("project_id", "")),
        "judge_peer_id": judge_peer_id,
        "scores": scores,
        "total": round(float(obj["total"]), 2),
        "feedback": str(obj["feedback"]),
        "interactions_summary": str(obj.get("interactions_summary", "")),
        "archetype": archetype["name"],
    }
