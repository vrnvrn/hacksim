"""Bounty composition. Two decision paths, same envelope shape.

With `ANTHROPIC_API_KEY` set, the run loop calls the Anthropic SDK
against the BountyDesigner persona prompt and the human prompt, then
parses one bounty out of the response. Without a key, a deterministic
stub runs instead, varying output by the designer's peer id and the
human prompt so each sponsor on the mesh produces a distinct, on-theme
bounty.

The stub is not a placeholder. The demo runs cleanly without
`ANTHROPIC_API_KEY` in the environment, which matters for first-time
reviewers and CI.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Any

from packages.agents._anthropic import call_with_retry, make_client

from .persona import SPONSORS, load_persona_text, sponsor_for_peer_id


# Deterministic prize tiers per sponsor: stub mode picks one of these.
_PRIZE_TIERS = {
    "Helix Capital": [3000, 4000, 5000],
    "FoldLab": [1000, 2000, 2500],
    "DeepProtein": [1500, 2000],
    "NorthStar": [1000, 1500, 2000],
    "Lumen": [500, 1000, 1500],
    "Atlas Security": [2000, 2500, 3000],
    "Vector": [1500, 2000],
    "Drift": [500, 750, 1000],
}

# Per-sponsor qualifying bullet templates. Stub mode renders one set.
_STUB_QUAL = {
    "FoldLab": [
        "uses a biological dataset or simulator",
        "shows a working demo with a real input",
        "explains the science in plain language",
    ],
    "Helix Capital": [
        "implements a working market mechanism",
        "demonstrates at least three trading scenarios",
        "documents the failure modes of the design",
    ],
    "DeepProtein": [
        "applies an ML model to a biological signal",
        "reports a quantitative metric on a held-out set",
        "publishes the prompts or training recipe",
    ],
    "NorthStar": [
        "renders a map or graph with at least two layers",
        "supports interactive panning or zooming",
        "explains the routing or scoring logic",
    ],
    "Lumen": [
        "instruments a running system with traces",
        "displays the trace tree in a usable UI",
        "writes one paragraph on what surprised the author",
    ],
    "Atlas Security": [
        "uses encryption or zero-knowledge primitives",
        "documents the threat model the design covers",
        "ships a working demo a non-expert can use",
    ],
    "Vector": [
        "embeds at least 1000 documents",
        "supports both lexical and semantic queries",
        "reports a side-by-side latency comparison",
    ],
    "Drift": [
        "supports two or more concurrent users",
        "shows live presence or cursors",
        "handles disconnect and reconnect cleanly",
    ],
}

_STUB_TITLES = {
    "FoldLab": "Best Protein Visualisation Tool",
    "Helix Capital": "Best Onchain Prediction Market Primitive",
    "DeepProtein": "Best Use of an ML Model on Biological Data",
    "NorthStar": "Best Interactive Mapping Demo",
    "Lumen": "Best Observability Surface for an Agent System",
    "Atlas Security": "Best Privacy Primitive Demo",
    "Vector": "Best Hybrid Retrieval Stack",
    "Drift": "Best Real-Time Collaborative Toy",
}


def propose_bounty(
    *,
    sim_prompt: str,
    sender_peer_id: str,
    api_key: str | None = None,
    emit: Any = None,
) -> dict[str, Any]:
    """Return one bounty payload as a dict matching the Bounty schema.

    Tries Anthropic SDK if `api_key` (or ANTHROPIC_API_KEY) is set; falls
    back to the deterministic stub otherwise. Caller broadcasts the
    return value as a `bounty.posted` envelope payload.

    `emit`, when supplied, is the role worker's `state.emit` so SDK
    failures land on the SSE stream as `decision.anthropic_failed` rather
    than falling through silently.
    """
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if key:
        try:
            return _propose_via_anthropic(
                sim_prompt=sim_prompt,
                sender_peer_id=sender_peer_id,
                api_key=key,
                emit=emit,
            )
        except Exception:
            # `_propose_via_anthropic` already emitted the structured
            # failure event through `call_with_retry`; fall back to the stub.
            pass
    return _propose_stub(sim_prompt=sim_prompt, sender_peer_id=sender_peer_id)


def _propose_stub(*, sim_prompt: str, sender_peer_id: str) -> dict[str, Any]:
    """Deterministic bounty derived from the designer's peer id and the prompt."""
    sponsor = sponsor_for_peer_id(sender_peer_id)
    name = sponsor["name"]
    niche = sponsor["niche"]

    # Mix in the sim prompt so two sims with different prompts produce
    # different bounty titles for the same sponsor.
    h = hashlib.sha256(f"{sender_peer_id}|{sim_prompt}".encode("utf-8")).digest()
    prize_options = _PRIZE_TIERS.get(name, [1000, 2000])
    prize = prize_options[h[1] % len(prize_options)]

    title = _STUB_TITLES.get(name, f"Best {name} Project")
    description = (
        f"{name} sponsors work in {niche}. "
        f"In the context of '{sim_prompt.strip()[:120]}', "
        f"we want to see a self-contained demo a curious peer can run and play with."
    )
    qualification = list(_STUB_QUAL.get(name, ["working demo", "clear documentation", "novel approach"]))

    return {
        "title": title,
        "sponsor_name": name,
        "prize_amount_usd": prize,
        "description": description,
        "qualification": qualification,
    }


def _propose_via_anthropic(
    *,
    sim_prompt: str,
    sender_peer_id: str,
    api_key: str,
    emit: Any = None,
) -> dict[str, Any]:
    """Call Anthropic SDK to compose a bounty. Validates the JSON.

    Lazy-imports `anthropic` via the shared helper so this module stays
    importable when the SDK is missing (CI uses the stub).
    """
    sponsor = sponsor_for_peer_id(sender_peer_id)
    persona = load_persona_text()
    user_prompt = (
        f"The hackathon prompt: \"{sim_prompt}\"\n\n"
        f"Your sponsor archetype is {sponsor['name']}, niche: {sponsor['niche']}.\n"
        f"Compose exactly one bounty as JSON only."
    )

    client = make_client(api_key)
    response = call_with_retry(
        lambda: client.messages.create(
            model=os.environ.get("HACKSIM_MODEL", "claude-haiku-4-5-20251001"),
            max_tokens=1024,
            system=persona,
            messages=[{"role": "user", "content": user_prompt}],
        ),
        operation="propose_bounty",
        emit=emit,
    )
    text = "".join(block.text for block in response.content if hasattr(block, "text")).strip()
    return _parse_bounty_json(text, fallback_sponsor=sponsor["name"])


_BOUNTY_REQUIRED = {"title", "sponsor_name", "prize_amount_usd", "description", "qualification"}


def _parse_bounty_json(text: str, fallback_sponsor: str) -> dict[str, Any]:
    """Pull the first JSON object out of a possibly-noisy response."""
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("no JSON object found in response")
    obj = json.loads(match.group(0))
    if not isinstance(obj, dict):
        raise ValueError("response JSON is not an object")
    missing = _BOUNTY_REQUIRED - obj.keys()
    if missing:
        raise ValueError(f"bounty missing fields: {sorted(missing)}")
    if not isinstance(obj["qualification"], list):
        raise ValueError("qualification must be a list")
    obj.setdefault("sponsor_name", fallback_sponsor)
    return obj
