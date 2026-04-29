import Link from "next/link";
import { Nav } from "@/components/Nav";
import { Footer } from "@/components/Footer";

const ITEMS: Array<{ title: string; body: string; href: string }> = [
  {
    title: "Architecture",
    body: "How the orchestrator, AXL nodes, and Claude Code sessions plug together. Includes the full message-flow diagram.",
    href: "https://github.com/gensyn-ai/axl",
  },
  {
    title: "Agents",
    body: "One page per role. Persona files verbatim, MCP tools surfaced, example envelopes for every event type.",
    href: "https://github.com/gensyn-ai/axl",
  },
  {
    title: "Process notes",
    body: "Per-commit notes with the same five-section shape. Read the build chronologically in fifteen minutes.",
    href: "https://github.com/gensyn-ai/axl",
  },
];

export default function DocsPage() {
  return (
    <>
      <Nav />
      <main className="max-w-7xl mx-auto px-6 lg:px-8 pt-20 pb-24">
        <h1 className="font-display text-5xl lg:text-6xl font-semibold text-ink leading-tight">
          Docs
        </h1>
        <p className="text-xl text-body mt-6 max-w-3xl leading-snug">
          Long-form documentation lives in the GitHub repo. The links below
          point at the canonical files. Every commit ships a matching process
          note.
        </p>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-12">
          {ITEMS.map((item) => (
            <Link
              key={item.title}
              href={item.href}
              target="_blank"
              rel="noreferrer"
              className="rounded-3xl border border-border p-6 hover:border-muted transition block"
            >
              <h2 className="font-display text-2xl font-semibold text-ink">
                {item.title}
              </h2>
              <p className="text-body mt-3 leading-relaxed">{item.body}</p>
            </Link>
          ))}
        </div>
      </main>
      <Footer />
    </>
  );
}
