"""Bounty selection. Deterministic skill-overlap scoring with optional
Anthropic SDK upgrade.
"""

from __future__ import annotations

import os
from typing import Any, Callable

from packages.agents._anthropic import call_with_retry, make_client

EmitFn = Callable[[str, dict[str, Any]], None]


def score_bounty_fit(*, bounty: dict[str, Any], skills: list[str]) -> int:
    """Return a non-negative integer score for how well the builder's
    skills fit the bounty. Higher is better. Tied scores break by
    bounty title alphabetical.

    Heuristic: count case-insensitive skill mentions in the bounty's
    title, description, and qualification list. Plus a small bonus for
    every direct skill overlap with the sponsor's niche keywords.
    """
    haystack = " ".join(
        [
            str(bounty.get("title", "")),
            str(bounty.get("description", "")),
            " ".join(str(q) for q in bounty.get("qualification", [])),
            str(bounty.get("sponsor_name", "")),
        ]
    ).lower()
    score = 0
    for skill in skills:
        if skill.lower() in haystack:
            score += 2
        # Loose token overlap: any word in the haystack matches the skill.
        for token in skill.lower().split():
            if token and token in haystack:
                score += 1
    return score


def pick_bounty(
    *,
    bounties: list[dict[str, Any]],
    skills: list[str],
    emit: EmitFn | None = None,
) -> dict[str, Any] | None:
    """Pick the best bounty from the list using `score_bounty_fit`.

    Returns None if the input list is empty. On ties, picks the one
    whose title sorts earliest so picks are reproducible across runs.

    `emit`, when supplied, is the role worker's `state.emit` so SDK
    failures land on the SSE stream as `decision.anthropic_failed`.
    """
    if not bounties:
        return None

    if api_key := os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return _pick_via_anthropic(
                bounties=bounties, skills=skills, api_key=api_key, emit=emit
            )
        except Exception:
            # Failure already surfaced via `decision.anthropic_failed`;
            # fall back to the deterministic scoring heuristic.
            pass

    scored = sorted(
        bounties,
        key=lambda b: (-score_bounty_fit(bounty=b, skills=skills), str(b.get("title", ""))),
    )
    return scored[0]


def _pick_via_anthropic(
    *,
    bounties: list[dict[str, Any]],
    skills: list[str],
    api_key: str,
    emit: EmitFn | None = None,
) -> dict[str, Any]:
    """Reasoned pick via Anthropic SDK. Returns one of the input bounties.

    Asks the model to return only the chosen bounty's id. We then look
    up the bounty in the input list. If the response is malformed we
    raise so the caller falls back to the scoring heuristic.
    """
    import json
    import re

    catalogue = [
        {
            "id": str(b.get("id", "")),
            "title": str(b.get("title", "")),
            "sponsor_name": str(b.get("sponsor_name", "")),
            "description": str(b.get("description", "")),
            "qualification": list(b.get("qualification", [])),
            "prize_amount_usd": int(b.get("prize_amount_usd", 0)),
        }
        for b in bounties
    ]

    user_prompt = (
        "Your skills: "
        + ", ".join(skills)
        + "\n\nBounties:\n"
        + json.dumps(catalogue, indent=2)
        + "\n\nReturn JSON only, with the single field 'bounty_id' set to "
          "the id of the bounty you choose."
    )

    client = make_client(api_key)
    response = call_with_retry(
        lambda: client.messages.create(
            model=os.environ.get("HACKSIM_MODEL", "claude-haiku-4-5-20251001"),
            max_tokens=128,
            system="You are a hackathon builder picking the bounty that best fits your skills.",
            messages=[{"role": "user", "content": user_prompt}],
        ),
        operation="pick_bounty",
        emit=emit,
    )
    text = "".join(block.text for block in response.content if hasattr(block, "text")).strip()
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("no JSON in response")
    obj = json.loads(match.group(0))
    chosen_id = str(obj.get("bounty_id", ""))
    for b in bounties:
        if str(b.get("id", "")) == chosen_id:
            return b
    raise ValueError(f"chosen bounty id {chosen_id!r} not in catalogue")
