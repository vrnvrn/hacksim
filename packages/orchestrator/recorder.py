"""Capture every event in a simulation to a JSON Lines file.

The recorder is the on-disk twin of the SSE hub: every event the hub
publishes for a given sim is appended to a file as `{"t": float,
"type": str, "data": dict}` so a replay route can stream the run back
later with the original timing.

Why this exists
---------------

The hosted Vercel preview is fixtures-only by default because a real run
needs a Go binary, a Python venv, and ~10 seconds of mesh boot. A
recorded run lets a judge see the live UI without that install: the
`/replay/<runId>` route reads the JSONL file, accumulates the snapshot,
and streams the events back at original (or compressed) cadence.

File format
-----------

The first line is a meta record::

    {"meta": {"sim_id": "...", "prompt": "...", "started_at": "...",
              "config": {...}, "schema_version": 1}}

Subsequent lines are events::

    {"t": 0.000, "type": "sim.created", "data": {...}}
    {"t": 0.012, "type": "axl.binary",  "data": {...}}
    {"t": 1.847, "type": "phase.tick",  "data": {...}}

`t` is seconds since the recording started, with millisecond resolution.
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1


@dataclass
class Recorder:
    """Append-only writer for a sim's event stream.

    Construct, call `open(meta=...)` once, then `record(type, data)` per
    event. Closing flushes and shuts the file. Threadsafe (the writer
    lock guards file IO so the hub can publish from any thread).
    """

    path: Path
    _file: Any = None
    _started: float | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _closed: bool = False
    events_written: int = 0

    def open(self, meta: dict[str, Any]) -> None:
        """Open the output file and write the meta record.

        `meta` should carry at least `sim_id`, `prompt`, `started_at`,
        and `config` so the replay route can rebuild the snapshot
        without inspecting the events.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.path.open("w", encoding="utf-8")
        meta_line = {"meta": {**meta, "schema_version": SCHEMA_VERSION}}
        self._file.write(json.dumps(meta_line, separators=(",", ":")) + "\n")
        self._file.flush()
        self._started = time.time()

    def record(self, event_type: str, data: dict[str, Any]) -> None:
        """Append one event line. Silent no-op if the recorder is closed."""
        if self._closed or self._file is None or self._started is None:
            return
        elapsed = round(time.time() - self._started, 3)
        line = {"t": elapsed, "type": event_type, "data": data}
        encoded = json.dumps(line, separators=(",", ":"))
        with self._lock:
            if self._closed or self._file is None:
                return
            self._file.write(encoded + "\n")
            self._file.flush()
            self.events_written += 1

    def close(self) -> None:
        """Flush and close. Idempotent."""
        with self._lock:
            if self._closed:
                return
            self._closed = True
            if self._file is not None:
                try:
                    self._file.close()
                except Exception:
                    pass
                self._file = None


def read_recording(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Load a recording file. Returns `(meta, events)`.

    Tolerates malformed lines; the meta record is required and must be
    on line one. If the meta line is missing or malformed, raises
    `ValueError` so the API layer can return 4xx with a useful message.
    """
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(str(path))

    meta: dict[str, Any] | None = None
    events: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fp:
        for line_num, raw in enumerate(fp, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if line_num == 1:
                m = obj.get("meta") if isinstance(obj, dict) else None
                if not isinstance(m, dict):
                    raise ValueError(
                        f"recording {path} missing meta record on line 1"
                    )
                meta = m
                continue
            if not isinstance(obj, dict):
                continue
            if "t" not in obj or "type" not in obj:
                continue
            events.append(obj)

    if meta is None:
        raise ValueError(f"recording {path} has no meta record")
    return meta, events
