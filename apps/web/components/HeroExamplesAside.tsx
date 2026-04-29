"use client";

import { useTransition } from "react";
import type { SimConfig } from "@/lib/types";
import { cn } from "@/lib/cn";

const PRESETS = [
  {
    title: "Onchain agents",
    prompt: "an onchain agents hackathon with five sponsors and a $5k pool",
    accent: "from-indigo-100 via-fuchsia-100 to-rose-100",
    glyph: "◇",
  },
  {
    title: "Research lab",
    prompt:
      "a research hackathon focused on protein folding tools and ML primitives, four sponsors",
    accent: "from-emerald-100 via-teal-100 to-cyan-100",
    glyph: "◎",
  },
  {
    title: "Indie agentic",
    prompt:
      "an indie agent hackathon, builders working on the weirdest agent town demos they can ship",
    accent: "from-amber-100 via-orange-100 to-pink-100",
    glyph: "▦",
  },
  {
    title: "Privacy primitives",
    prompt:
      "a privacy primitives hackathon, three sponsors funding ZK and encryption demos for non-experts",
    accent: "from-sky-100 via-blue-100 to-indigo-100",
    glyph: "◐",
  },
];

const DEFAULT_CONFIG: SimConfig = {
  builders: 8,
  judges: 3,
  designers: 3,
  duration_hint: "short",
};

export function HeroExamplesAside() {
  const [isPending, startTransition] = useTransition();

  function spinUp(prompt: string) {
    startTransition(async () => {
      try {
        const res = await fetch("/api/sim", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt, config: DEFAULT_CONFIG }),
        });
        if (!res.ok) throw new Error(`status ${res.status}`);
        const json = (await res.json()) as { id: string };
        window.location.href = `/sim/${json.id}`;
      } catch {
        // Fall back to the canned mock sim so the click still does something
        // visible when the orchestrator is unreachable.
        window.location.href = "/sim/sim_2026-04-28_a1b2c3";
      }
    });
  }

  return (
    <aside
      aria-labelledby="examples-aside-heading"
      className="rounded-3xl border border-border bg-canvas/60 p-5 lg:p-6"
    >
      <div className="flex items-baseline justify-between">
        <h2
          id="examples-aside-heading"
          className="font-display text-base font-semibold text-ink uppercase tracking-wide"
        >
          Or pick an example
        </h2>
        <span className="text-xs text-muted">click to spin up</span>
      </div>
      <ul className="mt-4 grid grid-cols-1 gap-2">
        {PRESETS.map((preset) => (
          <li key={preset.title}>
            <button
              type="button"
              onClick={() => spinUp(preset.prompt)}
              disabled={isPending}
              className={cn(
                "group w-full rounded-2xl border border-border bg-surface px-4 py-3 text-left",
                "hover:border-ink hover:shadow-soft transition",
                "focus:outline-none focus:ring-2 focus:ring-accent",
                "disabled:opacity-50 disabled:cursor-progress",
              )}
            >
              <div className="flex items-center gap-3">
                <span
                  aria-hidden="true"
                  className={cn(
                    "shrink-0 grid place-items-center w-10 h-10 rounded-xl bg-gradient-to-br text-ink text-lg font-mono",
                    preset.accent,
                  )}
                >
                  {preset.glyph}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-semibold text-ink">
                    {preset.title}
                  </div>
                  <div className="text-xs text-muted truncate">
                    {preset.prompt}
                  </div>
                </div>
                <span
                  aria-hidden="true"
                  className="shrink-0 text-muted group-hover:text-ink transition"
                >
                  &gt;
                </span>
              </div>
            </button>
          </li>
        ))}
      </ul>
    </aside>
  );
}
