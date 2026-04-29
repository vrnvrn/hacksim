"use client";

import type { Bounty, Project } from "@/lib/types";
import { Play } from "lucide-react";
import { cn } from "@/lib/cn";

const RIBBON: Record<1 | 2 | 3, { label: string; bg: string; text: string }> = {
  1: { label: "1st", bg: "bg-gold", text: "text-ink" },
  2: { label: "2nd", bg: "bg-silver", text: "text-ink" },
  3: { label: "3rd", bg: "bg-coral", text: "text-ink" },
};

const formatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

// Showcase page card. Renders a coloured ribbon (gold, silver, coral) for
// rank, the project title, the bounty it won, and a "Try it" button that
// opens the demo modal.
export function WinnerCard({
  project,
  rank,
  prize,
  onTryIt,
}: {
  project: Project;
  rank: 1 | 2 | 3;
  prize: Bounty;
  onTryIt: () => void;
}) {
  const r = RIBBON[rank];
  return (
    <article
      className="relative rounded-3xl border border-border bg-surface p-6 pt-12 hover:border-muted transition flex flex-col gap-3"
      aria-labelledby={`winner-${project.id}-title`}
    >
      <span
        className={cn(
          "absolute top-4 left-4 rounded-full px-3 py-1 text-xs font-semibold",
          r.bg,
          r.text,
        )}
        aria-label={`Rank ${r.label} for the ${prize.title} bounty`}
      >
        {r.label}
      </span>
      <p className="text-xs uppercase tracking-wide text-muted font-semibold">
        {prize.sponsor_name} · {formatter.format(prize.prize_amount_usd)}
      </p>
      <h3
        id={`winner-${project.id}-title`}
        className="font-display text-2xl font-semibold text-ink leading-tight"
      >
        {project.title}
      </h3>
      <p className="text-sm text-body leading-relaxed line-clamp-3">
        {project.tagline}
      </p>
      <button
        type="button"
        onClick={onTryIt}
        className="mt-2 inline-flex items-center gap-2 rounded-md bg-ink text-surface px-4 py-2 text-sm font-semibold w-fit hover:opacity-90 transition"
        aria-label={`Try ${project.title} in the demo modal`}
      >
        <Play className="h-3.5 w-3.5" aria-hidden />
        Try it
      </button>
    </article>
  );
}
