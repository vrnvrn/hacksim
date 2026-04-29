import type { Verdict } from "@/lib/types";

// Phase 4 leaderboard. One row per project, columns per judge, total at the
// far right. Sort happens at the call-site so the same component works for
// per-bounty leaderboards on the showcase page.
export function Verdicts({ verdicts }: { verdicts: Verdict[] }) {
  if (verdicts.length === 0) {
    return (
      <p className="text-sm text-muted">
        No verdicts yet. Verdicts arrive when judges close out a project.
      </p>
    );
  }

  // Group by project for a basic leaderboard. The showcase page renders this
  // as a small per-bounty table; the live page renders it once across all
  // projects.
  const byProject = new Map<string, Verdict[]>();
  for (const v of verdicts) {
    const arr = byProject.get(v.project_id) ?? [];
    arr.push(v);
    byProject.set(v.project_id, arr);
  }

  const rows = Array.from(byProject.entries())
    .map(([projectId, items]) => {
      const total = items.reduce((s, v) => s + v.total, 0) / items.length;
      return { projectId, items, total };
    })
    .sort((a, b) => b.total - a.total);

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="border-b border-border">
            <th className="text-left text-xs uppercase tracking-wide font-semibold text-muted py-2">
              Project
            </th>
            <th className="text-left text-xs uppercase tracking-wide font-semibold text-muted py-2">
              Judges
            </th>
            <th className="text-right text-xs uppercase tracking-wide font-semibold text-muted py-2">
              Average
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.projectId} className="border-b border-border/60">
              <td className="py-3 font-mono text-xs text-body">
                {row.projectId}
              </td>
              <td className="py-3 text-xs text-body">
                {row.items.length} of 3
              </td>
              <td className="py-3 text-right font-mono tabular-nums text-ink">
                {row.total.toFixed(2)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
