"""End-to-end smoke harness for HackSim with full choreography.

Spawns the organiser as the bootstrap node (the choreographer), three
bounty designers, four builders, and three judges. The organiser
drives the phase lifecycle by publishing phase ticks at the configured
pace. Re-broadcasts (commit 18) catch peers whose Yggdrasil tree had
not propagated when the first broadcast went out.

Use:

    make build-axl
    .venv/bin/python scripts/smoke_e2e.py

Output: per-role event lines, then the final leaderboard from the
organiser's hackathon.closed envelope.

Environment overrides:
    HACKSIM_PACE   smoke (default for this script), quick, medium, deep
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from packages.axl_client import AxlClient  # noqa: E402
from packages.orchestrator import Spawner  # noqa: E402

AXL_BIN = REPO / "third_party" / "axl" / "node"
RUN_DIR = Path("/tmp/hacksim_smoke")


def _events_for(handle, count: int = 0) -> list[dict]:
    """Read all JSON event lines from a role's worker log. Returns the
    last `count` if non-zero, otherwise the full list.
    """
    if not handle.worker_log_path.exists():
        return []
    text = handle.worker_log_path.read_text(encoding="utf-8")
    out: list[dict] = []
    for line in text.splitlines():
        try:
            out.append(json.loads(line))
        except Exception:
            pass
    return out[-count:] if count else out


def _summarise_payload(payload: dict, max_len: int = 220) -> str:
    summary = json.dumps(payload, separators=(",", ":"))
    if len(summary) > max_len:
        summary = summary[:max_len] + "..."
    return summary


def main() -> int:
    if not AXL_BIN.exists():
        print(f"AXL binary missing at {AXL_BIN}. run `make build-axl` first.")
        return 1
    if shutil.which("openssl") is None:
        print("openssl is required to generate ed25519 keys.")
        return 1

    if RUN_DIR.exists():
        shutil.rmtree(RUN_DIR)
    RUN_DIR.mkdir(parents=True)

    sim_id = "sim_smoke"
    pace = os.environ.setdefault("HACKSIM_PACE", "smoke")
    print(f"== HackSim smoke == run dir: {RUN_DIR} pace: {pace}")

    with Spawner(
        base_dir=RUN_DIR,
        axl_bin=AXL_BIN,
        sim_id=sim_id,
        api_port_base=9300,
    ) as spawner:
        # Organiser is the bootstrap. It schedules phase ticks on its own
        # so the harness does not have to inject them.
        organiser = spawner.spawn_role(role="organiser", index=0, is_bootstrap=True)

        designers = [spawner.spawn_role(role="bounty_designer", index=i) for i in range(3)]
        builders = [spawner.spawn_role(role="builder", index=i) for i in range(4)]
        judges = [spawner.spawn_role(role="judge", index=i) for i in range(3)]
        all_handles = (
            [("organiser", organiser)]
            + [("bounty_designer", h) for h in designers]
            + [("builder", h) for h in builders]
            + [("judge", h) for h in judges]
        )

        print(f"\nspawned {len(spawner.role_handles)} roles total")
        print(f"  organiser:  {organiser.node.spec.name} api {organiser.node.api_port}")
        print(f"  designers:  {len(designers)}")
        print(f"  builders:   {len(builders)}")
        print(f"  judges:     {len(judges)}")

        org_client = AxlClient(organiser.api_url)

        # Wait for the mesh to begin settling.
        print("\nwaiting up to 8s for at least one peer to appear ...")
        deadline = time.time() + 8.0
        while time.time() < deadline:
            try:
                if len(org_client.all_peer_ids()) >= 1:
                    break
            except Exception:
                pass
            time.sleep(0.5)
        try:
            print(f"  organiser sees {len(org_client.all_peer_ids())} peers initially")
        except Exception as e:
            print(f"  topology query failed: {e}")

        # The organiser scheduled phase ticks at startup; they will fire on
        # the configured pace. Wait for the close timestamp plus grace.
        from packages.agents.organiser.persona import PACE_PRESETS
        close_at = PACE_PRESETS.get(pace, PACE_PRESETS["smoke"])["close_at"]
        wait_for = close_at + 8.0
        print(f"\nrunning sim for {wait_for:.0f}s (until close_at + grace) ...")

        # Periodic heartbeat so we can see progress live.
        end_time = time.time() + wait_for
        last_announced = 0.0
        while time.time() < end_time:
            now = time.time()
            elapsed = wait_for - (end_time - now)
            if elapsed - last_announced >= 10.0:
                last_announced = elapsed
                # Find the most recent organiser event for a status line.
                events = _events_for(organiser)
                last = events[-1] if events else {}
                print(f"  t+{elapsed:>3.0f}s  last organiser event: {last.get('type', '(none)')}")
            time.sleep(2.0)

        print("\n== role event logs (filtered) ==")
        interesting_types = {
            "designer.composing", "bounty.posted",
            "builder.heard_bounty", "team.formed", "builder.building",
            "project.submitted", "builder.no_bounty", "builder.no_team",
            "judge.heard_project", "rubric.published", "verdict.published",
            "judge.no_projects",
            "organiser.scheduled", "phase.tick.broadcast", "hackathon.closed",
            "orch.registered", "orch.register_error",
        }
        for role, handle in all_handles:
            events = [e for e in _events_for(handle) if e.get("type") in interesting_types]
            if not events:
                continue
            print(f"\n-- {handle.node.spec.name} ({role}) --")
            for e in events[-12:]:
                print(f"  {e['type']}: {_summarise_payload(e.get('payload', {}))}")

        # Final leaderboard from the organiser.
        print("\n== final leaderboard ==")
        for e in _events_for(organiser):
            if e.get("type") == "hackathon.closed":
                p = e.get("payload", {})
                winners = p.get("winners", [])
                project_count = p.get("project_count", 0)
                verdict_count = p.get("verdict_count", 0)
                print(f"  {project_count} project(s), {verdict_count} verdict(s) tallied")
                for row in winners:
                    print(f"  rank {row['rank']}: {row['title']}")
                    print(f"    score: {row['total_score']}  verdicts: {row['verdicts']}")
                break
        else:
            print("  hackathon.closed not yet emitted")

        # Show every builder's artefact path.
        print("\n== builder artefacts ==")
        for role, handle in all_handles:
            if role != "builder":
                continue
            project_dir = handle.node.work_dir / "project"
            if project_dir.exists():
                files = sorted(p.name for p in project_dir.iterdir() if not p.name.startswith("."))
                print(f"  {handle.node.spec.name}: {project_dir}")
                print(f"    files: {files}")
                print(f"    open {project_dir / 'index.html'}")
            else:
                print(f"  {handle.node.spec.name}: no project")

        print("\nsmoke complete; tearing down ...")

    print("done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
