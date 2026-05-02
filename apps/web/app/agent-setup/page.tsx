import Link from "next/link";
import { Nav } from "@/components/Nav";
import { Footer } from "@/components/Footer";
import { AgentInstructions } from "@/components/AgentInstructions";

export const metadata = {
  title: "Agent setup | HackSim",
  description:
    "Hand this block to your coding agent. It clones HackSim, installs the prerequisites, and starts the demo for you.",
};

export default function AgentSetupPage() {
  return (
    <>
      <Nav />
      <main className="max-w-4xl mx-auto px-6 lg:px-8 pt-12 lg:pt-16 pb-24">
        <p className="text-xs font-mono uppercase tracking-[0.18em] text-accent">
          [ paste into your coding agent ]
        </p>
        <h1 className="font-display text-4xl lg:text-5xl font-semibold text-ink leading-tight mt-3">
          Hand this to your coding agent.
        </h1>
        <p className="text-base lg:text-lg text-body mt-4 leading-relaxed">
          Paste the block below into Claude Code, Cursor, GitHub Copilot, or any
          AI coding assistant on your machine. The agent will clone the repo,
          install everything, prompt you for an optional API key, and start the
          demo. About five minutes from copy to a live AXL mesh.
        </p>

        <div className="mt-8">
          <AgentInstructions />
        </div>

        <section
          aria-labelledby="what-this-does"
          className="mt-10 rounded-3xl border border-border p-6 lg:p-8 bg-canvas/50"
        >
          <h2
            id="what-this-does"
            className="font-display text-2xl font-semibold text-ink"
          >
            What this does
          </h2>
          <p className="text-body mt-3 leading-relaxed">
            The block is written for the agent, not for you. Your agent does
            the typing. It runs the canonical{" "}
            <code className="rounded bg-canvas px-1.5 py-0.5 font-mono text-[0.85em] text-ink">
              make demo
            </code>{" "}
            workflow: one organiser, three bounty designers, eight builders,
            and three judges, all peering through Yggdrasil on loopback. Every
            cross-agent byte goes through AXL.
          </p>
          <p className="text-sm text-body mt-3 leading-relaxed">
            Prereqs your agent will check for you: Go 1.25 or newer, Node 20
            with{" "}
            <code className="rounded bg-canvas px-1.5 py-0.5 font-mono text-[0.85em] text-ink">
              pnpm
            </code>
            , Python 3.10+, openssl. No accounts required. The demo runs
            without an Anthropic key on a deterministic stub that still
            produces real, distinct output.
          </p>
          <p className="text-sm text-body mt-3 leading-relaxed">
            For the per-second timing table and a manual verification path,
            see{" "}
            <Link
              href="/docs#run-it-locally"
              className="text-accent hover:underline"
            >
              the full quickstart on /docs
            </Link>
            .
          </p>
        </section>

        <p className="text-xs text-muted mt-10 leading-relaxed">
          Want a hosted version? See the deployment plan in the repo at{" "}
          <a
            href="https://github.com/vrnvrn/hacksim/blob/main/refs/HOSTED_DEMO_FLY_PLAN.md"
            target="_blank"
            rel="noreferrer"
            className="text-accent hover:underline"
          >
            refs/HOSTED_DEMO_FLY_PLAN.md
          </a>
          .
        </p>
      </main>
      <Footer />
    </>
  );
}
