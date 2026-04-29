"use client";

import * as Popover from "@radix-ui/react-popover";
import type { Builder } from "@/lib/types";

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .map((p) => p[0]!)
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

function shortPeer(peerId: string): string {
  if (peerId.length < 12) return peerId;
  return `${peerId.slice(0, 6)}...${peerId.slice(-4)}`;
}

// One builder. Click reveals the persona excerpt and the full skill list.
export function BuilderChip({
  builder,
  onSelect,
}: {
  builder: Builder;
  onSelect?: () => void;
}) {
  return (
    <Popover.Root>
      <Popover.Trigger asChild>
        <button
          type="button"
          onClick={onSelect}
          className="group flex items-center gap-3 rounded-2xl border border-border bg-surface px-3 py-2 hover:border-muted transition text-left"
          aria-label={`Builder ${builder.display_name}, ${builder.skills.length} skills`}
        >
          <span
            aria-hidden="true"
            className="h-9 w-9 rounded-full bg-accent-soft text-accent font-semibold flex items-center justify-center text-sm"
          >
            {initials(builder.display_name)}
          </span>
          <span className="min-w-0">
            <span className="block font-semibold text-sm text-ink truncate">
              {builder.display_name}
            </span>
            <span className="block text-xs text-muted truncate">
              {builder.skills.slice(0, 2).join(", ")}
              {builder.skills.length > 2 ? "..." : ""}
            </span>
          </span>
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          align="start"
          sideOffset={8}
          className="z-40 w-80 rounded-2xl border border-border bg-surface p-4 shadow-lg"
        >
          <p className="text-xs text-muted font-mono">
            peer {shortPeer(builder.peer_id)}
          </p>
          <h4 className="font-display text-lg font-semibold text-ink mt-1">
            {builder.display_name}
          </h4>
          <p className="text-xs text-muted mt-1">
            Team {builder.team_id ?? "unassigned"} ·{" "}
            {builder.current_bounty_id ? "working" : "idle"}
          </p>
          <div className="mt-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted">
              Skills
            </p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {builder.skills.map((s) => (
                <span
                  key={s}
                  className="text-xs px-2 py-0.5 rounded-full bg-canvas text-body border border-border"
                >
                  {s}
                </span>
              ))}
            </div>
          </div>
          {builder.persona_excerpt ? (
            <p className="text-sm text-body mt-3 leading-relaxed">
              {builder.persona_excerpt}
            </p>
          ) : null}
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
