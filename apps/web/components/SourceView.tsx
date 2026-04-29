"use client";

import { useEffect, useState } from "react";
import { Copy, Check } from "lucide-react";
import type { ProjectFile } from "@/lib/types";

// Right pane of the Code tab. We render the file content as a <pre><code>
// block. shiki is dynamically imported the first time a text file is opened,
// keeping the modal under its 60kB lazy budget when the user only views the
// Demo tab. Binary files get an inline preview (image) or a placeholder.
export function SourceView({
  file,
  content,
}: {
  file: ProjectFile;
  content: string;
}) {
  const [highlighted, setHighlighted] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let active = true;
    if (file.kind !== "text") {
      setHighlighted(null);
      return;
    }
    (async () => {
      try {
        const { codeToHtml } = await import("shiki");
        const lang = guessLang(file.path);
        const html = await codeToHtml(content, {
          lang,
          theme: "github-light",
        });
        if (active) setHighlighted(html);
      } catch {
        if (active) setHighlighted(null);
      }
    })();
    return () => {
      active = false;
    };
  }, [file.path, file.kind, content]);

  const lineCount = content.split(/\r?\n/).length;

  function copyToClipboard() {
    if (typeof navigator === "undefined") return;
    navigator.clipboard?.writeText(content).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    });
  }

  return (
    <div className="flex flex-col h-full">
      <header className="flex items-center justify-between px-4 py-2 border-b border-border bg-canvas text-xs">
        <div className="font-mono text-body truncate">{file.path}</div>
        <div className="flex items-center gap-3">
          <span className="text-muted">{lineCount} lines</span>
          <button
            type="button"
            onClick={copyToClipboard}
            className="inline-flex items-center gap-1 text-body hover:text-ink transition"
            aria-label="Copy file contents"
          >
            {copied ? (
              <Check className="h-3.5 w-3.5" aria-hidden />
            ) : (
              <Copy className="h-3.5 w-3.5" aria-hidden />
            )}
            {copied ? "Copied" : "Copy"}
          </button>
        </div>
      </header>
      <div className="flex-1 overflow-auto bg-surface">
        {file.kind === "image" ? (
          <ImagePreview path={file.path} />
        ) : file.kind === "binary" ? (
          <div className="p-6 text-sm text-muted">
            Binary file. Preview not available.
          </div>
        ) : highlighted ? (
          <div
            className="text-xs font-mono p-4 leading-relaxed [&_pre]:!bg-transparent"
            // shiki returns trusted, server-style HTML built from this exact content.
            dangerouslySetInnerHTML={{ __html: highlighted }}
          />
        ) : (
          <pre className="text-xs font-mono p-4 whitespace-pre overflow-x-auto">
            <code>{content}</code>
          </pre>
        )}
      </div>
    </div>
  );
}

function ImagePreview({ path }: { path: string }) {
  // The image is fetched via the static endpoint; the parent passes the URL
  // we should display as a separate prop in production. For now we render a
  // simple placeholder block so the layout is stable.
  return (
    <div className="p-6 flex items-center justify-center h-full">
      <div className="rounded-2xl border border-border bg-canvas p-10 text-center text-sm text-muted">
        Image preview: {path}
      </div>
    </div>
  );
}

function guessLang(path: string): string {
  const ext = path.split(".").pop()?.toLowerCase();
  switch (ext) {
    case "html":
      return "html";
    case "css":
      return "css";
    case "js":
    case "mjs":
    case "cjs":
      return "javascript";
    case "ts":
    case "tsx":
      return "typescript";
    case "json":
      return "json";
    case "md":
      return "markdown";
    case "svg":
    case "xml":
      return "xml";
    default:
      return "txt";
  }
}
