// Thin client wrappers around the orchestrator API. In mock mode the
// /api/mocks/* routes serve the same shapes from local fixtures so the entire
// app works end to end with no backend running.

import type { Project, ProjectFile, Snapshot } from "./types";

export const useMocks = () => process.env.NEXT_PUBLIC_USE_MOCKS === "true";

export function snapshotUrl(simId: string): string {
  return useMocks()
    ? `/api/mocks/snapshot?id=${encodeURIComponent(simId)}`
    : `/api/sim/${encodeURIComponent(simId)}/snapshot`;
}

export function streamUrl(simId: string): string {
  return useMocks()
    ? `/api/mocks/stream?id=${encodeURIComponent(simId)}`
    : `/api/sim/${encodeURIComponent(simId)}/stream`;
}

export function projectFilesUrl(simId: string, projectId: string): string {
  return useMocks()
    ? `/api/mocks/projects/${encodeURIComponent(projectId)}/files`
    : `/api/sim/${encodeURIComponent(simId)}/projects/${encodeURIComponent(projectId)}/files`;
}

export function projectFileUrl(
  simId: string,
  projectId: string,
  filePath: string,
): string {
  if (useMocks()) {
    return `/api/mocks/projects/${encodeURIComponent(projectId)}/files/${filePath}`;
  }
  return `/api/sim/${encodeURIComponent(simId)}/projects/${encodeURIComponent(projectId)}/files/${filePath}`;
}

export function projectStaticUrl(
  simId: string,
  projectId: string,
  filePath: string,
): string {
  if (useMocks()) {
    return `/api/mocks/projects/${encodeURIComponent(projectId)}/static/${filePath}`;
  }
  return `/api/sim/${encodeURIComponent(simId)}/projects/${encodeURIComponent(projectId)}/static/${filePath}`;
}

export async function getSnapshot(simId: string): Promise<Snapshot> {
  const res = await fetch(snapshotUrl(simId), { cache: "no-store" });
  if (!res.ok) throw new Error(`snapshot fetch failed: ${res.status}`);
  return (await res.json()) as Snapshot;
}

export async function getProjectFiles(
  simId: string,
  projectId: string,
): Promise<{
  project_id: string;
  commit_hash: string | null;
  entry_path: string;
  github_url: string | null;
  files: ProjectFile[];
}> {
  const res = await fetch(projectFilesUrl(simId, projectId), {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`files fetch failed: ${res.status}`);
  return res.json();
}

export async function getProjectFileContents(
  simId: string,
  projectId: string,
  filePath: string,
): Promise<string> {
  const res = await fetch(projectFileUrl(simId, projectId, filePath), {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`file fetch failed: ${res.status}`);
  return res.text();
}

export type WinnerEntry = {
  project: Project;
  rank: 1 | 2 | 3;
  total: number;
};

export function rankWinners(
  snapshot: Snapshot,
): Map<string, WinnerEntry[]> {
  const byBounty = new Map<string, WinnerEntry[]>();
  for (const bounty of snapshot.bounties) {
    const candidates = snapshot.projects.filter(
      (p) => p.bounty_id === bounty.id && p.status === "judged",
    );
    const totals = candidates
      .map((project) => {
        const verdicts = snapshot.verdicts.filter(
          (v) => v.project_id === project.id,
        );
        const total =
          verdicts.length === 0
            ? 0
            : verdicts.reduce((s, v) => s + v.total, 0) / verdicts.length;
        return { project, total };
      })
      .sort((a, b) => b.total - a.total);
    const entries: WinnerEntry[] = totals
      .slice(0, 3)
      .map((row, i) => ({
        project: row.project,
        rank: ((i + 1) as 1 | 2 | 3),
        total: row.total,
      }));
    byBounty.set(bounty.id, entries);
  }
  return byBounty;
}
