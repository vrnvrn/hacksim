"""hacksim-network skill commands.

Invoked by the slash commands defined in SKILL.md. Reads `AXL_API_PORT`,
`HACKSIM_ROLE`, and `HACKSIM_SIM_ID` from the environment, and calls the
AxlClient and protocol modules to broadcast and receive envelopes.

Port from the autoresearch demo's `research_network.py:177-307`. We
preserve the JSON-on-stdout discipline so the surrounding shell can pipe
output into other tools.

Slash command shell-out form (from SKILL.md):

    python -m packages.skills.hacksim_network.hacksim_network status
    python -m packages.skills.hacksim_network.hacksim_network recv
    python -m packages.skills.hacksim_network.hacksim_network post-bounty <<< '{...}'
    python -m packages.skills.hacksim_network.hacksim_network submit-project <<< '{...}'

Commands that need a JSON payload read it from stdin so the shell does
not have to deal with quoting.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from typing import Any

from packages.axl_client import AxlClient, AxlError
from packages.protocol import (
    Phase,
    decode_envelope,
    encode_envelope,
    is_known_event,
    make_envelope,
)


@dataclass
class SkillContext:
    """Per-run context derived from the environment."""

    api_url: str
    role: str
    sim_id: str

    @classmethod
    def from_env(cls) -> "SkillContext":
        port = os.environ.get("AXL_API_PORT")
        if not port:
            raise RuntimeError("AXL_API_PORT must be set")
        role = os.environ.get("HACKSIM_ROLE", "unknown")
        sim_id = os.environ.get("HACKSIM_SIM_ID", "")
        return cls(
            api_url=f"http://127.0.0.1:{port}",
            role=role,
            sim_id=sim_id,
        )

    def client(self) -> AxlClient:
        return AxlClient(self.api_url)


# ---------------------------------------------------------------- status ------


def cmd_status(ctx: SkillContext) -> dict[str, Any]:
    """Return our identity and topology summary as a dict."""
    client = ctx.client()
    topo = client.get_topology()
    return {
        "role": ctx.role,
        "sim_id": ctx.sim_id,
        "our_public_key": topo.our_public_key,
        "our_ipv6": topo.our_ipv6,
        "peer_count": len(client.all_peer_ids()),
        "direct_peers": len(topo.peers),
        "tree_size": len(topo.tree),
    }


# ---------------------------------------------------------------- recv --------


def cmd_recv(ctx: SkillContext, max_messages: int = 100) -> list[dict]:
    """Drain the local /recv queue and return decoded envelopes."""
    client = ctx.client()
    out: list[dict] = []
    for _ in range(max_messages):
        msg = client.recv()
        if msg is None:
            break
        try:
            env = decode_envelope(msg.data)
        except ValueError:
            continue  # skip messages that are not HackSim envelopes
        out.append(dict(env))
    return out


# --------------------------------------------------------------- broadcast ----


def _broadcast(ctx: SkillContext, env_type: str, round_: int, payload: dict) -> dict:
    """Fan-out an envelope to every peer. Returns send count."""
    if not is_known_event(env_type):
        raise ValueError(f"unknown event type: {env_type!r}")

    client = ctx.client()
    topo = client.get_topology()
    env = make_envelope(
        type=env_type,
        round=round_,
        sender_id=topo.our_public_key,
        payload=payload,
    )
    wire = encode_envelope(env)

    sent = 0
    failed: list[str] = []
    for peer_id in client.all_peer_ids():
        try:
            client.send(peer_id, wire)
            sent += 1
        except AxlError as e:
            failed.append(f"{peer_id[:16]}:{e.status}")
    return {
        "envelope_type": env_type,
        "round": round_,
        "sender_id": topo.our_public_key,
        "bytes": len(wire),
        "sent_to": sent,
        "failed": failed,
        "timestamp": env["timestamp"],
    }


def cmd_post_bounty(ctx: SkillContext, payload: dict) -> dict:
    """Designer only: broadcast a bounty.posted envelope.

    Required payload fields per UX_SPEC.md section 7 (`Bounty`):
    title, sponsor_name, prize_amount_usd, description, qualification.
    """
    if ctx.role not in ("designer", "bounty_designer", "organiser"):
        raise PermissionError(f"role {ctx.role!r} cannot post bounties")
    required = {"title", "sponsor_name", "prize_amount_usd", "description"}
    missing = required - payload.keys()
    if missing:
        raise ValueError(f"payload missing fields: {sorted(missing)}")
    payload.setdefault("qualification", [])
    return _broadcast(ctx, "bounty.posted", Phase.BOUNTY_DESIGN, payload)


def cmd_submit_project(ctx: SkillContext, payload: dict) -> dict:
    """Builder only: broadcast a project.submitted envelope.

    Required payload fields per PLAN.md section 5:
    project_id, team_id, bounty_id, title, tagline, commit_hash,
    entry_path, working_dir.
    """
    if ctx.role not in ("builder",):
        raise PermissionError(f"role {ctx.role!r} cannot submit projects")
    required = {
        "project_id",
        "team_id",
        "bounty_id",
        "title",
        "tagline",
        "commit_hash",
        "entry_path",
        "working_dir",
    }
    missing = required - payload.keys()
    if missing:
        raise ValueError(f"payload missing fields: {sorted(missing)}")
    return _broadcast(ctx, "project.submitted", Phase.BUILD, payload)


# -------------------------------------------------------------------- main ----


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint. Each command writes JSON to stdout and exits 0/1."""
    parser = argparse.ArgumentParser(prog="hacksim-network")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    sub.add_parser("recv")
    sub.add_parser("post-bounty")
    sub.add_parser("submit-project")

    args = parser.parse_args(argv)

    try:
        ctx = SkillContext.from_env()
        if args.cmd == "status":
            result: Any = cmd_status(ctx)
        elif args.cmd == "recv":
            result = cmd_recv(ctx)
        elif args.cmd == "post-bounty":
            payload = json.loads(sys.stdin.read())
            result = cmd_post_bounty(ctx, payload)
        elif args.cmd == "submit-project":
            payload = json.loads(sys.stdin.read())
            result = cmd_submit_project(ctx, payload)
        else:
            parser.error(f"unknown command: {args.cmd}")
            return 2
    except (AxlError, ValueError, PermissionError, RuntimeError) as e:
        sys.stderr.write(f"hacksim-network: {e}\n")
        return 1

    sys.stdout.write(json.dumps(result, indent=2))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
