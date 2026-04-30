"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ChevronDown, ChevronUp, Pause, Play } from "lucide-react";
import { useSse } from "@/lib/use-sse";
import type { Envelope } from "@/lib/types";
import { cn } from "@/lib/cn";

const MAX_LINES = 500;
const HOSTED_REPLAY =
  process.env.NEXT_PUBLIC_HOSTED_PREVIEW === "true" &&
  process.env.NEXT_PUBLIC_USE_MOCKS === "true";

function shortPeer(peer: string | undefined): string {
  if (!peer) return "anon";
  if (peer.length < 12) return peer;
  return `${peer.slice(0, 6)}...${peer.slice(-4)}`;
}

function summarise(env: Envelope): string {
  // Prefer a "title" or "id" field when present so the line reads like a
  // newspaper headline.
  const d = env.data ?? {};
  const interesting = [
    "title",
    "project_id",
    "bounty_id",
    "team_id",
    "phase",
    "score",
  ];
  const parts: string[] = [];
  for (const k of interesting) {
    if (k in d) {
      const value = d[k];
      const stringValue =
        typeof value === "string"
          ? value
          : typeof value === "number" || typeof value === "boolean"
            ? String(value)
            : null;
      if (stringValue !== null) {
        parts.push(`${k}: ${stringValue}`);
      }
    }
  }
  return parts.length > 0 ? `{${parts.join(", ")}}` : "{}";
}

// Right-rail terminal pane. Listens to the SSE stream, appends one line per
// envelope, auto-scrolls unless the user has scrolled up. A pause toggle
// freezes the view without dropping events. On mobile (sm and below) the
// pane collapses by default to a single header row so the SubmissionsGrid
// is reachable without scrolling past 80vh of run log.
export function RunLog({ simId }: { simId: string }) {
  const [lines, setLines] = useState<Envelope[]>([]);
  const [paused, setPaused] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const liveRef = useRef<HTMLDivElement | null>(null);

  // Collapse by default on narrow viewports. Reads window.matchMedia once
  // on mount, no resize listener (the user can collapse / expand
  // manually after that).
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (window.matchMedia("(max-width: 1023px)").matches) {
      setCollapsed(true);
    }
  }, []);

  const onEvent = useCallback((env: Envelope) => {
    setLines((prev) => {
      const next = [...prev, env];
      if (next.length > MAX_LINES) {
        return next.slice(-MAX_LINES);
      }
      return next;
    });
  }, []);

  const { connected } = useSse(simId, onEvent);

  useEffect(() => {
    const node = containerRef.current;
    if (!node || paused) return;
    // Auto-scroll to the bottom unless the user is scrolled up by more than
    // a screen and a half. Treat that as "they are reading history."
    const distanceFromBottom =
      node.scrollHeight - node.scrollTop - node.clientHeight;
    if (distanceFromBottom < node.clientHeight * 1.5) {
      node.scrollTop = node.scrollHeight;
    }
  }, [lines, paused]);

  // Announce only the most recent envelope to assistive tech, polite.
  const lastLine = lines[lines.length - 1];

  return (
    <aside
      className={cn(
        "rounded-3xl bg-navy-950 text-canvas font-mono text-xs flex flex-col overflow-hidden",
        collapsed ? "h-auto" : "h-[80vh]",
      )}
      aria-label="Run log"
    >
      <header className="flex items-center justify-between px-4 py-2 border-b border-white/10">
        <span className="text-[11px] uppercase tracking-wide text-canvas/70 flex items-center gap-2">
          Run log
          {HOSTED_REPLAY
            ? " · replay"
            : connected
              ? " · live"
              : " · offline"}
          {collapsed && lines.length > 0 ? (
            <span className="text-canvas/50">
              ({lines.length} event{lines.length === 1 ? "" : "s"})
            </span>
          ) : null}
        </span>
        <span className="flex items-center gap-3">
          {!collapsed ? (
            <button
              type="button"
              onClick={() => setPaused((v) => !v)}
              className="inline-flex items-center gap-1 text-[11px] text-canvas/80 hover:text-canvas transition"
              aria-label={paused ? "Resume run log auto-scroll" : "Pause run log auto-scroll"}
            >
              {paused ? (
                <Play className="h-3 w-3" aria-hidden />
              ) : (
                <Pause className="h-3 w-3" aria-hidden />
              )}
              {paused ? "Resume" : "Pause"}
            </button>
          ) : null}
          <button
            type="button"
            onClick={() => setCollapsed((v) => !v)}
            className="inline-flex items-center gap-1 text-[11px] text-canvas/80 hover:text-canvas transition"
            aria-label={collapsed ? "Expand run log" : "Collapse run log"}
            aria-expanded={!collapsed}
          >
            {collapsed ? (
              <ChevronDown className="h-3 w-3" aria-hidden />
            ) : (
              <ChevronUp className="h-3 w-3" aria-hidden />
            )}
            {collapsed ? "Expand" : "Collapse"}
          </button>
        </span>
      </header>
      {collapsed ? null : (<>

      <div
        ref={containerRef}
        className={cn(
          "runlog-pane flex-1 overflow-y-auto px-4 py-3 space-y-1",
        )}
      >
        {lines.length === 0 ? (
          <p className="text-canvas/40">
            Booting the agents... first events arrive in about five seconds.
          </p>
        ) : null}
        {lines.map((env, i) => (
          <RunLine key={i} env={env} />
        ))}
      </div>
      <div ref={liveRef} aria-live="polite" className="visually-hidden">
        {lastLine
          ? `${lastLine.type} from ${shortPeer(lastLine.from)}`
          : ""}
      </div>
      </>)}
    </aside>
  );
}

function RunLine({ env }: { env: Envelope }) {
  const ts = env.ts ?? new Date().toISOString();
  return (
    <p className="leading-relaxed">
      <span className="text-canvas/40">[{ts}]</span>{" "}
      <span className="text-accent">{env.type}</span>{" "}
      <span className="text-canvas/60">from {shortPeer(env.from)} -&gt;</span>{" "}
      <span className="text-canvas/90">{summarise(env)}</span>
    </p>
  );
}
