"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import type { Judge, Project, Verdict } from "@/lib/types";

// Inside the ProjectDemoModal Verdict tab. Shows the rubric, then a
// per-judge accordion with the score table and prose feedback. Empty state
// kicks in when the project has not been judged yet.
export function VerdictPanel({
  project,
  verdicts,
  judges,
}: {
  project: Project;
  verdicts: Verdict[];
  judges: Judge[];
}) {
  const judgeVerdicts = verdicts.filter((v) => v.project_id === project.id);

  if (project.status !== "judged" || judgeVerdicts.length === 0) {
    return (
      <div className="p-8 text-body">
        <p className="text-base">This project has not been judged yet.</p>
        <p className="text-sm text-muted mt-2">
          The Verdict tab populates the moment the last judge publishes a
          score for this project.
        </p>
      </div>
    );
  }

  const totals = judgeVerdicts.map((v) => v.total).sort((a, b) => a - b);
  const average =
    totals.reduce((s, n) => s + n, 0) / Math.max(totals.length, 1);
  const median =
    totals.length === 0
      ? 0
      : totals.length % 2 === 1
        ? totals[(totals.length - 1) / 2]!
        : (totals[totals.length / 2 - 1]! + totals[totals.length / 2]!) / 2;
  const spread = totals.length > 1 ? totals[totals.length - 1]! - totals[0]! : 0;

  // Use the first judge's rubric as the canonical structure for the table.
  const rubric = judges[0]?.rubric ?? [];

  return (
    <div className="p-6 space-y-6">
      <header>
        <h2 className="font-display text-2xl font-semibold text-ink">
          Verdict
        </h2>
        <p className="text-sm text-body mt-1">
          Average: {average.toFixed(1)}/10. Median: {median.toFixed(1)}.{" "}
          {judgeVerdicts.length} judges scored.
          {spread > 2 ? (
            <span className="ml-2 text-coral font-medium">
              Spread of opinion.
            </span>
          ) : null}
        </p>
      </header>

      {rubric.length > 0 ? (
        <section className="rounded-2xl border border-border bg-canvas p-5">
          <h3 className="font-semibold text-ink">Rubric</h3>
          <ul className="mt-3 space-y-2">
            {rubric.map((c) => (
              <li
                key={c.name}
                className="flex items-start justify-between gap-4 text-sm"
              >
                <div>
                  <p className="font-medium text-ink">{c.name}</p>
                  <p className="text-muted text-xs">{c.description}</p>
                </div>
                <span className="text-xs font-mono text-body">
                  {(c.weight * 100).toFixed(0)}%
                </span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section>
        <h3 className="font-semibold text-ink">Per-judge scores</h3>
        <div className="mt-3 space-y-3">
          {judgeVerdicts.map((verdict) => {
            const judge = judges.find(
              (j) => j.peer_id === verdict.judge_peer_id,
            );
            return (
              <JudgeAccordionItem
                key={verdict.judge_peer_id}
                verdict={verdict}
                judge={judge}
              />
            );
          })}
        </div>
      </section>
    </div>
  );
}

function JudgeAccordionItem({
  verdict,
  judge,
}: {
  verdict: Verdict;
  judge: Judge | undefined;
}) {
  const [open, setOpen] = useState(false);
  const name = judge?.display_name ?? "Unknown judge";
  return (
    <article className="rounded-2xl border border-border bg-surface overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between gap-3 p-4 hover:bg-canvas transition text-left"
        aria-expanded={open}
      >
        <span className="flex items-center gap-2">
          {open ? (
            <ChevronDown className="h-4 w-4 text-muted" aria-hidden="true" />
          ) : (
            <ChevronRight className="h-4 w-4 text-muted" aria-hidden="true" />
          )}
          <span className="font-semibold text-ink">{name}</span>
        </span>
        <span className="text-2xl font-display font-semibold tabular-nums">
          {verdict.total.toFixed(1)}
        </span>
      </button>
      {open ? (
        <div className="px-5 pb-5 space-y-3 text-sm">
          <table className="w-full">
            <thead>
              <tr className="text-left text-xs text-muted uppercase tracking-wide">
                <th className="py-1">Criterion</th>
                <th className="py-1">Weight</th>
                <th className="py-1 text-right">Score</th>
                <th className="py-1 text-right">Weighted</th>
              </tr>
            </thead>
            <tbody>
              {(judge?.rubric ?? []).map((c) => {
                const score = verdict.scores[c.name] ?? 0;
                return (
                  <tr key={c.name} className="border-t border-border/60">
                    <td className="py-1.5 text-ink">{c.name}</td>
                    <td className="py-1.5 text-body">
                      {(c.weight * 100).toFixed(0)}%
                    </td>
                    <td className="py-1.5 text-right font-mono tabular-nums text-ink">
                      {score.toFixed(1)}
                    </td>
                    <td className="py-1.5 text-right font-mono tabular-nums text-body">
                      {(score * c.weight).toFixed(2)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <p className="text-body leading-relaxed">{verdict.feedback}</p>
          {verdict.interactions_summary ? (
            <p className="text-xs text-muted italic">
              Playwright notes: {verdict.interactions_summary}
            </p>
          ) : null}
        </div>
      ) : null}
    </article>
  );
}
