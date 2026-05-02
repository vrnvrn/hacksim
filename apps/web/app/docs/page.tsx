import Link from "next/link";
import { Nav } from "@/components/Nav";
import { Footer } from "@/components/Footer";
import { Faq } from "@/components/Faq";
import { RunItLocally } from "@/components/RunItLocally";

const REPO = "https://github.com/vrnvrn/hacksim";

const ITEMS: Array<{ title: string; body: string; href: string }> = [
  {
    title: "Architecture",
    body: "How the FastAPI orchestrator, the AXL nodes, and the role workers fit together. Includes the message-flow diagram and the four AXL surfaces HackSim exercises (topology, send, recv, mcp).",
    href: `${REPO}/blob/main/docs/ARCHITECTURE.md`,
  },
  {
    title: "Agents",
    body: "One page per role: organiser, bounty designer, builder, judge. Persona files in full, inbound and outbound envelopes for every event type, deterministic vs Claude decision module split.",
    href: `${REPO}/blob/main/docs/AGENTS.md`,
  },
  {
    title: "Process notes",
    body: "Per-commit notes with the same five-section shape: what changed, why, how to verify, the AXL surface used, what comes next. Read the build chronologically in fifteen minutes.",
    href: `${REPO}/tree/main/docs/process`,
  },
];

const ABOUT_AXL = [
  "AXL is Gensyn's Agent eXchange Layer. It is a single Go binary that gives any application an encrypted peer-to-peer communication layer with no servers, no cloud, and no accounts. Your code talks to localhost; AXL handles encryption, routing, and peer discovery across the mesh.",
  "HackSim runs one AXL node per role in the simulation. Every cross-agent message goes through Yggdrasil; every byte is end-to-end encrypted. The orchestrator only spawns processes and serves the UI.",
];

export default function DocsPage() {
  return (
    <>
      <Nav />
      <main className="max-w-7xl mx-auto px-6 lg:px-8 pt-12 lg:pt-16 pb-24">
        <p className="text-xs font-mono uppercase tracking-[0.18em] text-accent">
          [ ETHGlobal Open Agents 2026 ]
        </p>
        <h1 className="font-display text-4xl lg:text-5xl font-semibold text-ink leading-tight mt-3">
          Docs
        </h1>
        <p className="text-base lg:text-lg text-body mt-4 max-w-3xl leading-relaxed">
          HackSim is a hackathon simulator built at ETHGlobal Open Agents 2026
          for the Gensyn AXL bounty. The links below point at canonical files
          in our public repo. Every commit ships a matching process note.
        </p>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-10">
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

        <RunItLocally />

        <Faq />

        <section
          aria-labelledby="about-axl"
          className="mt-16 rounded-3xl border border-border p-8 bg-canvas/50"
        >
          <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted">
            [ background ]
          </p>
          <h2
            id="about-axl"
            className="font-display text-2xl font-semibold text-ink mt-2"
          >
            About AXL
          </h2>
          {ABOUT_AXL.map((p, i) => (
            <p key={i} className="text-body mt-3 leading-relaxed max-w-3xl">
              {p}
            </p>
          ))}
          <p className="text-sm text-muted mt-5">
            Read the full AXL docs at{" "}
            <a
              href="https://docs.gensyn.ai/tech/agent-exchange-layer"
              target="_blank"
              rel="noreferrer"
              className="text-accent hover:underline"
            >
              docs.gensyn.ai/tech/agent-exchange-layer
            </a>
            . The AXL source is at{" "}
            <a
              href="https://github.com/gensyn-ai/axl"
              target="_blank"
              rel="noreferrer"
              className="text-accent hover:underline"
            >
              github.com/gensyn-ai/axl
            </a>
            .
          </p>
        </section>
      </main>
      <Footer />
    </>
  );
}
