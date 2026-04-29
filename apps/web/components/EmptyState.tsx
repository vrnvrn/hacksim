import type { ReactNode } from "react";

// Generic empty-state card. Used by the showcase page when no project clears
// the rubric, by the Verdict tab before judging completes, and anywhere the
// data is legitimately absent. Visually a calm card, never an error.
export function EmptyState({
  title,
  body,
  cta,
}: {
  title: string;
  body: string;
  cta?: ReactNode;
}) {
  return (
    <div
      className="rounded-3xl border border-border bg-canvas p-10 text-center"
      role="status"
    >
      <h2 className="font-display text-2xl font-semibold text-ink">{title}</h2>
      <p className="mt-3 text-body max-w-prose mx-auto leading-relaxed">{body}</p>
      {cta ? <div className="mt-6 flex justify-center">{cta}</div> : null}
    </div>
  );
}
