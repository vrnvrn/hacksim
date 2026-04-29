"use client";

import { useEffect, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import * as Tabs from "@radix-ui/react-tabs";
import { Info, X } from "lucide-react";
import {
  getProjectFileContents,
  getProjectFiles,
  projectStaticUrl,
} from "@/lib/api";
import type {
  Bounty,
  Builder,
  Judge,
  Project,
  ProjectFile,
  Verdict,
} from "@/lib/types";
import { FileTree } from "./FileTree";
import { SourceView } from "./SourceView";
import { VerdictPanel } from "./VerdictPanel";

export type ProjectDemoModalProps = {
  simId: string;
  projectId: string;
  open: boolean;
  onClose: () => void;
  // Optional context, fed from the surrounding snapshot. The modal works with
  // just (simId, projectId, open, onClose) but renders a richer header when
  // these are passed in.
  project?: Project;
  bounty?: Bounty;
  builders?: Builder[];
  judges?: Judge[];
  verdicts?: Verdict[];
};

type FilesPayload = {
  project_id: string;
  commit_hash: string | null;
  entry_path: string;
  github_url: string | null;
  files: ProjectFile[];
};

// Centerpiece modal: Demo, Code, Verdict tabs. The Demo tab is the moment the
// experience crosses from "watchable" to "playable". Sandbox attributes are
// locked per UX_SPEC §3.
export function ProjectDemoModal({
  simId,
  projectId,
  open,
  onClose,
  project,
  bounty,
  builders = [],
  judges = [],
  verdicts = [],
}: ProjectDemoModalProps) {
  const [files, setFiles] = useState<FilesPayload | null>(null);
  const [selectedPath, setSelectedPath] = useState<string>("index.html");
  const [content, setContent] = useState<string>("");
  const [loadingContent, setLoadingContent] = useState(false);

  // Fetch the file tree the first time the modal opens.
  useEffect(() => {
    if (!open) return;
    let alive = true;
    (async () => {
      try {
        const payload = (await getProjectFiles(simId, projectId)) as FilesPayload;
        if (!alive) return;
        setFiles(payload);
        setSelectedPath(payload.entry_path);
      } catch {
        if (!alive) return;
        setFiles({
          project_id: projectId,
          commit_hash: null,
          entry_path: "index.html",
          github_url: null,
          files: [],
        });
      }
    })();
    return () => {
      alive = false;
    };
  }, [open, simId, projectId]);

  // Fetch contents on selection change.
  useEffect(() => {
    if (!open || !files) return;
    const file = files.files.find((f) => f.path === selectedPath);
    if (!file || file.kind !== "text") {
      setContent("");
      return;
    }
    let alive = true;
    setLoadingContent(true);
    (async () => {
      try {
        const text = await getProjectFileContents(simId, projectId, selectedPath);
        if (alive) setContent(text);
      } catch {
        if (alive) setContent("");
      } finally {
        if (alive) setLoadingContent(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [open, files, selectedPath, simId, projectId]);

  const teamMembers = builders
    .filter(
      (b) =>
        b.team_id != null &&
        project?.team_id != null &&
        b.team_id === project.team_id,
    )
    .map((b) => b.display_name);

  return (
    <Dialog.Root open={open} onOpenChange={(o) => (o ? null : onClose())}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-ink/60 backdrop-blur-sm z-40 data-[state=open]:animate-in data-[state=open]:fade-in" />
        <Dialog.Content
          className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50 max-w-7xl w-[90vw] h-[90vh] rounded-3xl bg-surface p-0 overflow-hidden shadow-2xl flex flex-col focus:outline-none"
          aria-describedby={undefined}
        >
          <Dialog.Title className="visually-hidden">
            {project ? `Demo of ${project.title}` : "Project demo"}
          </Dialog.Title>

          <header className="flex items-center justify-between gap-4 px-6 py-4 border-b border-border">
            <div className="min-w-0">
              <h2 className="font-display text-xl font-semibold text-ink truncate">
                {project?.title ?? "Project"}
              </h2>
              <p className="text-xs text-muted truncate">
                {teamMembers.length > 0
                  ? `Team: ${teamMembers.join(", ")} · `
                  : ""}
                {bounty
                  ? `Bounty: ${bounty.title} · `
                  : ""}
                {files?.commit_hash
                  ? `commit ${files.commit_hash.slice(0, 7)}`
                  : project?.commit_hash
                    ? `commit ${project.commit_hash.slice(0, 7)}`
                    : "no commit"}
              </p>
            </div>
            <Dialog.Close asChild>
              <button
                type="button"
                aria-label="Close demo modal"
                className="rounded-full p-2 hover:bg-canvas transition"
              >
                <X className="h-5 w-5" aria-hidden />
              </button>
            </Dialog.Close>
          </header>

          <Tabs.Root
            defaultValue="demo"
            className="flex-1 flex flex-col min-h-0"
          >
            <Tabs.List
              className="flex items-center gap-1 px-6 border-b border-border"
              aria-label="Project tabs"
            >
              <TabTrigger value="demo">Demo</TabTrigger>
              <TabTrigger value="code">Code</TabTrigger>
              <TabTrigger value="verdict">Verdict</TabTrigger>
            </Tabs.List>

            <Tabs.Content value="demo" className="flex-1 min-h-0 flex flex-col">
              <div
                role="status"
                className="bg-warning-soft text-ink text-xs px-4 py-2 flex items-center gap-2"
              >
                <Info className="h-3.5 w-3.5" aria-hidden />
                <span>
                  Sandboxed agent-generated code. Cannot access your data,
                  cannot make network calls.
                </span>
              </div>
              <iframe
                src={projectStaticUrl(simId, projectId, project?.entry_path ?? files?.entry_path ?? "index.html")}
                sandbox="allow-scripts"
                className="w-full flex-1 bg-canvas"
                title={`Demo of ${project?.title ?? "project"}`}
              />
            </Tabs.Content>

            <Tabs.Content
              value="code"
              className="flex-1 min-h-0 grid grid-cols-[240px_1fr]"
            >
              <div className="border-r border-border bg-canvas">
                <FileTree
                  files={files?.files ?? []}
                  selectedPath={selectedPath}
                  onSelect={setSelectedPath}
                />
              </div>
              <div className="min-h-0 flex flex-col">
                {(files?.files.find((f) => f.path === selectedPath)) ? (
                  <SourceView
                    file={files!.files.find((f) => f.path === selectedPath)!}
                    content={loadingContent ? "Loading..." : content}
                  />
                ) : (
                  <div className="p-6 text-sm text-muted">
                    Pick a file from the tree.
                  </div>
                )}
              </div>
            </Tabs.Content>

            <Tabs.Content value="verdict" className="flex-1 min-h-0 overflow-y-auto">
              {project ? (
                <VerdictPanel
                  project={project}
                  verdicts={verdicts}
                  judges={judges}
                />
              ) : (
                <p className="p-6 text-sm text-muted">
                  Verdict context unavailable.
                </p>
              )}
            </Tabs.Content>
          </Tabs.Root>

          {files?.github_url ? (
            <footer className="border-t border-border px-6 py-3 bg-canvas text-xs text-body">
              <a
                href={files.github_url}
                target="_blank"
                rel="noreferrer"
                className="hover:text-ink transition"
              >
                View full repo on GitHub
              </a>
            </footer>
          ) : null}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function TabTrigger({
  value,
  children,
}: {
  value: string;
  children: React.ReactNode;
}) {
  return (
    <Tabs.Trigger
      value={value}
      className="px-4 py-3 text-sm font-medium text-body data-[state=active]:text-ink data-[state=active]:border-b-2 data-[state=active]:border-accent transition"
    >
      {children}
    </Tabs.Trigger>
  );
}
