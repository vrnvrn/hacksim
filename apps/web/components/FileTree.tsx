"use client";

import { useMemo, useState } from "react";
import { ChevronDown, ChevronRight, File as FileIcon, Folder } from "lucide-react";
import type { ProjectFile } from "@/lib/types";
import { cn } from "@/lib/cn";

type Node =
  | { type: "file"; name: string; path: string; kind: ProjectFile["kind"]; size: number }
  | { type: "folder"; name: string; path: string; children: Node[] };

function buildTree(files: ProjectFile[]): Node[] {
  const root: Node[] = [];
  for (const f of files) {
    const parts = f.path.split("/");
    let level = root;
    let pathSoFar = "";
    parts.forEach((part, i) => {
      pathSoFar = pathSoFar ? `${pathSoFar}/${part}` : part;
      if (i === parts.length - 1) {
        level.push({
          type: "file",
          name: part,
          path: f.path,
          kind: f.kind,
          size: f.size_bytes,
        });
        return;
      }
      let folder = level.find(
        (n): n is Extract<Node, { type: "folder" }> =>
          n.type === "folder" && n.name === part,
      );
      if (!folder) {
        folder = { type: "folder", name: part, path: pathSoFar, children: [] };
        level.push(folder);
      }
      level = folder.children;
    });
  }
  // Sort: folders first, then files, both alphabetical.
  function sort(nodes: Node[]) {
    nodes.sort((a, b) => {
      if (a.type !== b.type) return a.type === "folder" ? -1 : 1;
      return a.name.localeCompare(b.name);
    });
    for (const n of nodes) {
      if (n.type === "folder") sort(n.children);
    }
  }
  sort(root);
  return root;
}

// Left pane of the Code tab. Folders expand on click. The selected file is
// highlighted and the parent passes a setter so the source view can update.
export function FileTree({
  files,
  selectedPath,
  onSelect,
}: {
  files: ProjectFile[];
  selectedPath: string;
  onSelect: (path: string) => void;
}) {
  const tree = useMemo(() => buildTree(files), [files]);
  return (
    <nav
      aria-label="Project files"
      className="text-sm overflow-y-auto h-full p-3"
    >
      <ul className="space-y-0.5">
        {tree.map((node) => (
          <TreeNode
            key={node.path}
            node={node}
            depth={0}
            selectedPath={selectedPath}
            onSelect={onSelect}
          />
        ))}
      </ul>
    </nav>
  );
}

function TreeNode({
  node,
  depth,
  selectedPath,
  onSelect,
}: {
  node: Node;
  depth: number;
  selectedPath: string;
  onSelect: (path: string) => void;
}) {
  const [open, setOpen] = useState(true);
  const padding = { paddingLeft: `${depth * 12 + 8}px` };

  if (node.type === "folder") {
    return (
      <li>
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="w-full flex items-center gap-1.5 hover:bg-canvas px-2 py-1 rounded-md text-body"
          style={padding}
          aria-expanded={open}
        >
          {open ? (
            <ChevronDown className="h-3.5 w-3.5 text-muted" aria-hidden />
          ) : (
            <ChevronRight className="h-3.5 w-3.5 text-muted" aria-hidden />
          )}
          <Folder className="h-3.5 w-3.5 text-muted" aria-hidden />
          <span>{node.name}</span>
        </button>
        {open ? (
          <ul className="space-y-0.5">
            {node.children.map((c) => (
              <TreeNode
                key={c.path}
                node={c}
                depth={depth + 1}
                selectedPath={selectedPath}
                onSelect={onSelect}
              />
            ))}
          </ul>
        ) : null}
      </li>
    );
  }

  const selected = selectedPath === node.path;
  return (
    <li>
      <button
        type="button"
        onClick={() => onSelect(node.path)}
        className={cn(
          "w-full flex items-center gap-1.5 px-2 py-1 rounded-md hover:bg-canvas transition",
          selected ? "bg-accent-soft text-accent font-medium" : "text-body",
        )}
        style={padding}
        aria-current={selected ? "true" : undefined}
      >
        <span className="w-3.5" aria-hidden />
        <FileIcon className="h-3.5 w-3.5 text-muted" aria-hidden />
        <span className="truncate">{node.name}</span>
      </button>
    </li>
  );
}
