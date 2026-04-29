"use client";

import type { Project } from "@/lib/types";
import { StatPill } from "./StatPill";
import { cn } from "@/lib/cn";
import { Play } from "lucide-react";

const STATUS_LABEL: Record<Project["status"], string> = {
  drafting: "Drafting",
  submitted: "Submitted",
  judged: "Judged",
};

const STATUS_TONE: Record<Project["status"], "muted" | "success" | "accent"> = {
  drafting: "muted",
  submitted: "success",
  judged: "accent",
};

// Project tile, used on the hero "Example runs" grid and on the live page
// "Submissions" grid. Submitted and judged projects show a "Try it" CTA that
// opens the ProjectDemoModal.
export function ProjectTile({
  project,
  onTryIt,
  className,
  showCta = true,
}: {
  project: Project;
  onTryIt?: (id: string) => void;
  className?: string;
  showCta?: boolean;
}) {
  const canTry = showCta && project.status !== "drafting";
  return (
    <article
      className={cn(
        "rounded-3xl border border-border bg-surface p-6 hover:border-muted transition flex flex-col gap-4",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs uppercase tracking-wide text-muted font-semibold">
            {project.commit_hash
              ? `commit ${project.commit_hash.slice(0, 7)}`
              : "in progress"}
          </p>
          <h3 className="font-display text-2xl font-semibold text-ink mt-1 leading-tight">
            {project.title}
          </h3>
          <p className="text-sm text-body mt-1">{project.tagline}</p>
        </div>
        <StatPill
          label={STATUS_LABEL[project.status]}
          tone={STATUS_TONE[project.status]}
        />
      </div>
      <p className="text-sm text-body leading-relaxed line-clamp-3">
        {project.description}
      </p>
      <div className="mt-auto flex items-center justify-between">
        {canTry ? (
          <button
            type="button"
            onClick={() => onTryIt?.(project.id)}
            className="inline-flex items-center gap-2 rounded-md bg-ink text-surface px-4 py-2 text-sm font-semibold hover:opacity-90 transition"
            aria-label={`Try ${project.title} in the demo modal`}
          >
            <Play className="h-3.5 w-3.5" aria-hidden="true" />
            Try it
          </button>
        ) : (
          <span className="text-xs text-muted">No artefact yet</span>
        )}
        {project.github_url ? (
          <a
            href={project.github_url}
            target="_blank"
            rel="noreferrer"
            className="text-xs text-muted hover:text-ink transition"
          >
            View on GitHub
          </a>
        ) : null}
      </div>
    </article>
  );
}
