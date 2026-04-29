import type { Bounty } from "@/lib/types";
import { StatPill } from "./StatPill";

const formatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

// Single bounty card. Shown in the live page Bounties grid. The prize amount
// is the visual anchor; sponsor name is secondary; qualification list is the
// crisp acceptance criteria the builders read.
export function BountyCard({ bounty }: { bounty: Bounty }) {
  return (
    <article
      className="rounded-3xl border border-border p-6 bg-surface hover:border-muted transition"
      aria-labelledby={`bounty-${bounty.id}-title`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-wide text-muted font-semibold">
            {bounty.sponsor_name}
          </p>
          <h3
            id={`bounty-${bounty.id}-title`}
            className="font-display text-2xl font-semibold text-ink mt-1 leading-tight"
          >
            {bounty.title}
          </h3>
        </div>
        <StatPill
          label={formatter.format(bounty.prize_amount_usd)}
          tone="accent"
        />
      </div>
      <p className="text-body mt-3 leading-relaxed">{bounty.description}</p>
      {bounty.qualification.length > 0 ? (
        <div className="mt-4">
          <p className="text-xs font-semibold text-muted uppercase tracking-wide">
            Qualification
          </p>
          <ul className="mt-2 space-y-1 text-sm text-body list-disc list-inside">
            {bounty.qualification.map((q) => (
              <li key={q}>{q}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </article>
  );
}
