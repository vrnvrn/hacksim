"""Artefact store for project submissions.

When a builder broadcasts `project.submitted`, the role worker also
POSTs the same payload to the orchestrator. The orchestrator then runs
`git archive` on the builder's working directory at the named commit
hash and copies the tree into `sim-runs/{sim_id}/projects/{project_id}/`.

The static-file routes serve those archived trees with a strict
Content-Security-Policy that allows scripts and styles only from
'self' (and inline, since agent-generated code commonly inlines).
The CSP, the iframe sandbox attribute on the frontend, and the lack of
cookies together keep the agent code in a tight bag.

Path traversal is rejected at the store layer: any `..` or absolute
path component in the requested file is refused.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CSP_HEADER = (
    "default-src 'none'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "font-src 'self' data:; "
    "frame-ancestors 'self'"
)


class ArtefactError(RuntimeError):
    """Raised when an archive operation fails or a path is rejected."""


@dataclass
class ArtefactRecord:
    """A registered project artefact, served from the orchestrator."""

    sim_id: str
    project_id: str
    commit_hash: str
    entry_path: str
    base_dir: Path  # the served root for this project
    title: str
    tagline: str

    def files(self) -> list[dict[str, Any]]:
        """Return file metadata for the Code tab in the demo modal."""
        out: list[dict[str, Any]] = []
        for path in sorted(self.base_dir.rglob("*")):
            if path.is_dir():
                continue
            rel = path.relative_to(self.base_dir).as_posix()
            if rel.startswith(".") or rel.startswith("__"):
                continue  # skip dotfiles and the title/tagline metadata files
            out.append(
                {
                    "path": rel,
                    "size_bytes": path.stat().st_size,
                    "kind": _kind_for(path),
                }
            )
        return out


class ArtefactStore:
    """Owns the on-disk archive of every submitted project for every sim."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self._records: dict[tuple[str, str], ArtefactRecord] = {}
        if not self.base_dir.exists():
            self.base_dir.mkdir(parents=True)

    def register(self, sim_id: str, payload: dict[str, Any]) -> ArtefactRecord:
        """Archive the working tree referenced by `payload` and return the record.

        Required payload fields: `project_id`, `working_dir`, `commit_hash`,
        `entry_path`. Optional: `title`, `tagline`.

        Idempotent: re-registering the same (sim_id, project_id) replaces
        the archive in place.
        """
        try:
            project_id = str(payload["project_id"])
            working_dir = Path(str(payload["working_dir"]))
            commit_hash = str(payload["commit_hash"])
            entry_path = str(payload["entry_path"])
        except KeyError as e:
            raise ArtefactError(f"payload missing field: {e.args[0]!r}") from e

        if not working_dir.exists():
            raise ArtefactError(f"working_dir does not exist: {working_dir}")
        if not (working_dir / ".git").exists():
            raise ArtefactError(f"working_dir is not a git repo: {working_dir}")

        target = self.base_dir / sim_id / "projects" / project_id
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)

        # `git archive --format=tar <commit> | tar -x -C target` is the
        # canonical pattern. We pipe via subprocess directly.
        archive_proc = subprocess.Popen(
            ["git", "archive", "--format=tar", commit_hash],
            cwd=working_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        extract_proc = subprocess.Popen(
            ["tar", "-x", "-C", str(target)],
            stdin=archive_proc.stdout,
            stderr=subprocess.PIPE,
        )
        if archive_proc.stdout is not None:
            archive_proc.stdout.close()
        extract_err = extract_proc.communicate()[1]
        archive_err = archive_proc.communicate()[1]

        if archive_proc.returncode != 0:
            raise ArtefactError(
                f"git archive failed: {archive_err.decode('utf-8', 'replace')}"
            )
        if extract_proc.returncode != 0:
            raise ArtefactError(
                f"tar extract failed: {extract_err.decode('utf-8', 'replace')}"
            )

        record = ArtefactRecord(
            sim_id=sim_id,
            project_id=project_id,
            commit_hash=commit_hash,
            entry_path=entry_path,
            base_dir=target,
            title=str(payload.get("title", "Project")),
            tagline=str(payload.get("tagline", "")),
        )
        self._records[(sim_id, project_id)] = record
        return record

    def get(self, sim_id: str, project_id: str) -> ArtefactRecord | None:
        return self._records.get((sim_id, project_id))

    def list_for_sim(self, sim_id: str) -> list[ArtefactRecord]:
        return [r for (sid, _pid), r in self._records.items() if sid == sim_id]

    def safe_path(self, sim_id: str, project_id: str, rel: str) -> Path | None:
        """Resolve `rel` against the project's base dir, refusing traversal.

        Returns None if the project is unknown, the path resolves outside
        the base dir, or the path includes any `..` component.
        """
        record = self.get(sim_id, project_id)
        if record is None:
            return None
        # Reject any path that has a `..` component or is absolute.
        if rel.startswith("/") or ".." in Path(rel).parts:
            return None
        candidate = (record.base_dir / rel).resolve()
        try:
            candidate.relative_to(record.base_dir.resolve())
        except ValueError:
            return None
        return candidate


def _kind_for(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}:
        return "image"
    if suffix in {".woff", ".woff2", ".ttf", ".otf", ".eot"}:
        return "binary"
    return "text"
