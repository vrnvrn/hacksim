import type { Judge } from "@/lib/types";

function shortPeer(peerId: string): string {
  if (peerId.length < 12) return peerId;
  return `${peerId.slice(0, 6)}...${peerId.slice(-4)}`;
}

// One judge card on the live page. Shows the rubric the judge wrote (their
// own opinion of what good looks like) and a live counter of progress.
export function JudgePanel({ judge }: { judge: Judge }) {
  const progressPct =
    judge.total_to_score === 0
      ? 0
      : Math.round((judge.scored_count / judge.total_to_score) * 100);

  return (
    <article
      className="rounded-3xl border border-border bg-surface p-6"
      aria-labelledby={`judge-${judge.peer_id}-title`}
    >
      <div className="flex items-baseline justify-between gap-3">
        <div>
          <p className="text-xs font-mono text-muted">
            peer {shortPeer(judge.peer_id)}
          </p>
          <h3
            id={`judge-${judge.peer_id}-title`}
            className="font-display text-xl font-semibold text-ink mt-1"
          >
            {judge.display_name}
          </h3>
        </div>
        <span className="text-xs font-semibold text-accent">
          scored {judge.scored_count} of {judge.total_to_score}
        </span>
      </div>

      <div
        className="mt-3 h-1.5 w-full bg-canvas rounded-full overflow-hidden"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={progressPct}
        aria-label={`Scoring progress, ${progressPct} percent`}
      >
        <div
          className="h-full bg-accent transition-[width] duration-500"
          style={{ width: `${progressPct}%` }}
        />
      </div>

      <div className="mt-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted">
          Rubric
        </p>
        <ul className="mt-2 space-y-2">
          {judge.rubric.map((c) => (
            <li
              key={c.name}
              className="flex items-start justify-between gap-3 text-sm"
            >
              <div>
                <p className="font-medium text-ink">{c.name}</p>
                <p className="text-muted text-xs leading-relaxed">
                  {c.description}
                </p>
              </div>
              <span className="text-xs font-mono text-body shrink-0">
                {(c.weight * 100).toFixed(0)}%
              </span>
            </li>
          ))}
        </ul>
      </div>
    </article>
  );
}
