"""Build a single-page web project for a bounty.

Stub mode renders a clean, interactive index.html plus app.js plus
style.css from a template, varying by sponsor and skills so two
builders working on the same bounty produce visibly different output.
With ANTHROPIC_API_KEY set, the project is composed by Claude with the
sponsor's qualification list as the rubric.

The build function returns a dict carrying the working tree files. The
caller writes them, runs git, and broadcasts project.submitted.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from packages.agents._anthropic import call_with_retry, get_model, make_client

EmitFn = Callable[[str, dict[str, Any]], None]


def write_project(
    *,
    work_dir: Path,
    bounty: dict[str, Any],
    skills: list[str],
    sender_peer_id: str,
    sim_prompt: str = "",
    emit: EmitFn | None = None,
) -> dict[str, Any]:
    """Materialise project files into `work_dir`, git commit, return metadata.

    Returns: {commit_hash, entry_path, files: [{path, size_bytes}], title, tagline}.

    `emit`, when supplied, is the role worker's `state.emit` so SDK
    failures land on the SSE stream as `decision.anthropic_failed`.
    """
    work_dir.mkdir(parents=True, exist_ok=True)

    files = _compose_project(
        bounty=bounty,
        skills=skills,
        sender_peer_id=sender_peer_id,
        sim_prompt=sim_prompt,
        emit=emit,
    )

    for rel, content in files.items():
        path = work_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    commit_hash = _git_commit_all(work_dir, message=f"build: {files['__title']}")

    return {
        "commit_hash": commit_hash,
        "entry_path": "index.html",
        "title": files["__title"],
        "tagline": files["__tagline"],
        "files": [
            {"path": rel, "size_bytes": len(content.encode("utf-8")), "kind": "text"}
            for rel, content in files.items()
            if not rel.startswith("__")
        ],
    }


def _compose_project(
    *,
    bounty: dict[str, Any],
    skills: list[str],
    sender_peer_id: str,
    sim_prompt: str,
    emit: EmitFn | None = None,
) -> dict[str, str]:
    """Return a map of relative path -> file contents.

    The dict also carries `__title` and `__tagline` keys that the caller
    passes back in the project.submitted envelope.
    """
    if api_key := os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return _compose_via_anthropic(
                bounty=bounty,
                skills=skills,
                sender_peer_id=sender_peer_id,
                sim_prompt=sim_prompt,
                api_key=api_key,
                emit=emit,
            )
        except Exception:
            # Failure already emitted via `decision.anthropic_failed`;
            # fall back to the stub composition so the run still produces
            # a real, judgable artefact.
            pass
    return _compose_stub(bounty=bounty, skills=skills, sender_peer_id=sender_peer_id)


def _compose_stub(
    *,
    bounty: dict[str, Any],
    skills: list[str],
    sender_peer_id: str,
) -> dict[str, str]:
    """Deterministic template, varies by sponsor and peer id."""
    title = f"{bounty.get('title', 'Project')} by {sender_peer_id[:6]}"
    tagline = f"A submission for {bounty.get('sponsor_name', 'an unnamed sponsor')}."

    # Pick an accent hue from the peer id so two builders produce visibly
    # distinct demos even on the same bounty.
    h = hashlib.sha256(sender_peer_id.encode("ascii")).digest()
    hue = h[0]
    skill_pills = "".join(f'<span class="pill">{s}</span>' for s in skills)
    qualification_items = "".join(
        f"<li>{q}</li>" for q in bounty.get("qualification", []) or []
    )
    description = bounty.get("description", "")
    sponsor = bounty.get("sponsor_name", "")
    bounty_title = bounty.get("title", "")

    index_html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>{title}</title>
<link rel="stylesheet" href="style.css" />
</head>
<body>
<header>
  <p class="kicker">{sponsor}</p>
  <h1>{bounty_title}</h1>
  <p class="tagline">{tagline}</p>
  <div class="pills">{skill_pills}</div>
</header>
<main>
  <section class="card">
    <h2>What this is</h2>
    <p>{description}</p>
    <h2>Qualification</h2>
    <ul>{qualification_items}</ul>
  </section>
  <section class="card interactive">
    <h2>Try the prototype</h2>
    <p>Click the canvas to drop a node. Drag a node to move it. The
       graph adjusts as you go.</p>
    <canvas id="canvas" width="640" height="360"></canvas>
    <button id="reset">Reset</button>
    <output id="status"></output>
  </section>
</main>
<script src="app.js"></script>
</body>
</html>
"""

    style_css = f""":root {{
  --accent: hsl({hue}, 70%, 55%);
  --accent-soft: hsl({hue}, 90%, 95%);
  --ink: #111827;
  --body: #374151;
  --muted: #6b7280;
  --border: #d1d5db;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  font-family: ui-sans-serif, system-ui, -apple-system, sans-serif;
  color: var(--body);
  background: #fafafa;
  min-height: 100vh;
}}
header {{
  padding: 48px 32px 32px;
  background: linear-gradient(180deg, var(--accent-soft), #fafafa);
  border-bottom: 1px solid var(--border);
}}
.kicker {{ color: var(--accent); text-transform: uppercase; letter-spacing: .08em; font-weight: 600; font-size: 12px; margin: 0; }}
h1 {{ color: var(--ink); font-size: 36px; margin: 8px 0; line-height: 1.1; }}
.tagline {{ color: var(--muted); margin: 0 0 16px; font-size: 18px; }}
.pills {{ display: flex; gap: 8px; flex-wrap: wrap; }}
.pill {{ background: white; border: 1px solid var(--border); border-radius: 999px; padding: 4px 12px; font-size: 12px; color: var(--ink); }}
main {{ padding: 32px; display: grid; gap: 24px; grid-template-columns: minmax(0, 1fr) minmax(0, 1.3fr); max-width: 1100px; margin: 0 auto; }}
.card {{ background: white; border: 1px solid var(--border); border-radius: 24px; padding: 24px; }}
.card h2 {{ color: var(--ink); font-size: 18px; margin: 0 0 8px; }}
.card ul {{ margin: 8px 0 0 18px; padding: 0; }}
.card li {{ margin: 4px 0; }}
.interactive canvas {{ width: 100%; height: 360px; background: #f3f4f6; border-radius: 12px; cursor: crosshair; display: block; margin-top: 12px; }}
.interactive button {{ margin-top: 12px; background: var(--accent); color: white; border: none; padding: 8px 16px; border-radius: 8px; font-weight: 600; cursor: pointer; }}
.interactive button:hover {{ opacity: 0.9; }}
.interactive output {{ display: block; margin-top: 8px; color: var(--muted); font-size: 13px; }}
@media (max-width: 720px) {{ main {{ grid-template-columns: 1fr; }} }}
"""

    app_js = """const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");
const status = document.getElementById("status");
const reset = document.getElementById("reset");

let nodes = [];
let dragging = null;

function rescale() {
  const ratio = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * ratio;
  canvas.height = rect.height * ratio;
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
}

function draw() {
  rescale();
  const rect = canvas.getBoundingClientRect();
  ctx.clearRect(0, 0, rect.width, rect.height);

  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      const a = nodes[i], b = nodes[j];
      const d = Math.hypot(a.x - b.x, a.y - b.y);
      const alpha = Math.max(0, 1 - d / 240);
      if (alpha > 0) {
        ctx.strokeStyle = `rgba(99, 102, 241, ${alpha.toFixed(2)})`;
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
      }
    }
  }
  for (const n of nodes) {
    ctx.fillStyle = "#6366f1";
    ctx.beginPath();
    ctx.arc(n.x, n.y, 8, 0, Math.PI * 2);
    ctx.fill();
  }
  status.textContent = nodes.length + " nodes on canvas. Drag to move, click to add.";
}

function nodeAt(x, y) {
  for (let i = nodes.length - 1; i >= 0; i--) {
    const n = nodes[i];
    if (Math.hypot(n.x - x, n.y - y) < 12) return n;
  }
  return null;
}

canvas.addEventListener("mousedown", (e) => {
  const rect = canvas.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const y = e.clientY - rect.top;
  const hit = nodeAt(x, y);
  if (hit) { dragging = hit; return; }
  nodes.push({ x, y });
  draw();
});

canvas.addEventListener("mousemove", (e) => {
  if (!dragging) return;
  const rect = canvas.getBoundingClientRect();
  dragging.x = e.clientX - rect.left;
  dragging.y = e.clientY - rect.top;
  draw();
});

canvas.addEventListener("mouseup", () => { dragging = null; });

reset.addEventListener("click", () => { nodes = []; draw(); });

window.addEventListener("resize", draw);
draw();
"""

    return {
        "index.html": index_html,
        "style.css": style_css,
        "app.js": app_js,
        "__title": title,
        "__tagline": tagline,
    }


_MIN_INDEX_HTML_BYTES = 200


def _compose_via_anthropic(
    *,
    bounty: dict[str, Any],
    skills: list[str],
    sender_peer_id: str,
    sim_prompt: str,
    api_key: str,
    emit: EmitFn | None = None,
) -> dict[str, str]:
    """Ask Claude to compose a single-page web project as JSON files.

    Returns {index.html, style.css?, app.js?, __title, __tagline}.
    """
    user_prompt = (
        f"Hackathon prompt: \"{sim_prompt}\"\n"
        f"Bounty: {json.dumps({k: bounty.get(k) for k in ['title', 'sponsor_name', 'description', 'qualification']}, indent=2)}\n"
        f"Your skills: {', '.join(skills)}\n"
        f"Your peer id (for randomisation): {sender_peer_id[:8]}\n\n"
        "Write a compact single-page web project that satisfies the bounty's "
        "qualification list. Keep it tight: target around 2 KB of HTML plus 1 KB "
        "each of CSS and JS. Prefer a small working interactive demo over a "
        "long landing page. Self-contained: index.html plus optional style.css "
        "and app.js. No external network calls (CSP blocks them). No external "
        "scripts. Vanilla JS or import maps only.\n\n"
        "Respond with JSON only. The JSON has keys 'title' (string), 'tagline' "
        "(string), and 'files' (object mapping filename to file contents). Do "
        "not include any prose, just the JSON. Stay under 3500 tokens of output."
    )

    # 60s timeout: this call asks for up to 4096 tokens of HTML/CSS/JS,
    # which Claude haiku 4.5 reliably needs 15-30s to produce. The default
    # 10s timeout aborted every compose mid-stream, dropped every builder to
    # the deterministic stub, and submissions arrived after JUDGING closed.
    client = make_client(api_key, timeout=60.0)
    response = call_with_retry(
        lambda: client.messages.create(
            model=get_model(),
            max_tokens=4096,
            system="You are a hackathon builder. Write small, well-crafted web projects.",
            messages=[{"role": "user", "content": user_prompt}],
        ),
        operation="compose_project",
        emit=emit,
    )
    text = "".join(block.text for block in response.content if hasattr(block, "text")).strip()
    # Mid-tag truncation. Claude returns `stop_reason="max_tokens"` when
    # the budget runs out. We refuse the response so the caller falls
    # back to the stub instead of writing half an `<html>` document the
    # judge sees on the Code tab. Lift HACKSIM_MODEL to a roomier model
    # if this trips repeatedly.
    if getattr(response, "stop_reason", None) == "max_tokens":
        if emit is not None:
            emit(
                "decision.anthropic_truncated",
                {"operation": "compose_project", "max_tokens": 4096},
            )
        raise ValueError("response hit max_tokens before completing")
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("no JSON in response")
    obj = json.loads(match.group(0))
    files = obj.get("files") or {}
    if "index.html" not in files:
        raise ValueError("response missing index.html")
    if len(files["index.html"].encode("utf-8")) < _MIN_INDEX_HTML_BYTES:
        # A 50-byte index.html is almost always a model that emitted a
        # placeholder under truncation pressure. Demand a real document.
        raise ValueError("index.html shorter than minimum size")
    out = {**files, "__title": obj.get("title", "Project"), "__tagline": obj.get("tagline", "")}
    return out


def _git_commit_all(work_dir: Path, *, message: str) -> str:
    """Initialise a git repo if needed, stage everything, commit, return short hash."""
    git_dir = work_dir / ".git"
    if not git_dir.exists():
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=work_dir, check=True)
        subprocess.run(
            ["git", "config", "user.email", "builder@hacksim.local"],
            cwd=work_dir,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "HackSim Builder"],
            cwd=work_dir,
            check=True,
        )

    subprocess.run(["git", "add", "-A"], cwd=work_dir, check=True)
    # Allow empty commits in case nothing changed; we want a hash anyway.
    subprocess.run(
        ["git", "commit", "--allow-empty", "-q", "-m", message],
        cwd=work_dir,
        check=True,
    )
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=work_dir,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()
