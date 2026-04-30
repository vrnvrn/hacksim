import Link from "next/link";

// Three-column footer at the bottom of the hero. Gray canvas surface to give
// the page a clear base. Last column has the GitHub link, per UX_SPEC §2.
export function Footer() {
  return (
    <footer className="bg-canvas mt-24 py-16" role="contentinfo">
      <div className="max-w-7xl mx-auto px-6 lg:px-8 grid grid-cols-1 md:grid-cols-3 gap-12">
        <div>
          <h2 className="font-display font-semibold text-xl text-ink">HackSim</h2>
          <p className="text-body text-sm mt-3 max-w-xs leading-relaxed">
            Run your own hackathon with agents. Built at ETHGlobal Open Agents
            2026 for the Gensyn AXL bounty. Open source, MIT.
          </p>
        </div>
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-muted">
            Built on
          </h3>
          <ul className="mt-3 space-y-2 text-sm">
            <li>
              <a
                href="https://docs.gensyn.ai/tech/agent-exchange-layer"
                className="text-body hover:text-ink transition"
                target="_blank"
                rel="noreferrer"
              >
                Gensyn AXL
              </a>
            </li>
            <li>
              <a
                href="https://www.anthropic.com/claude"
                className="text-body hover:text-ink transition"
                target="_blank"
                rel="noreferrer"
              >
                Anthropic Claude
              </a>
            </li>
            <li>
              <a
                href="https://ethglobal.com/events/agents"
                className="text-body hover:text-ink transition"
                target="_blank"
                rel="noreferrer"
              >
                ETHGlobal Open Agents 2026
              </a>
            </li>
          </ul>
        </div>
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-muted">
            HackSim
          </h3>
          <ul className="mt-3 space-y-2 text-sm">
            <li>
              <a
                href="https://github.com/vrnvrn/hacksim"
                className="text-body hover:text-ink transition"
                target="_blank"
                rel="noreferrer"
              >
                github.com/vrnvrn/hacksim
              </a>
            </li>
            <li>
              <Link
                href="/docs"
                className="text-body hover:text-ink transition"
              >
                Docs
              </Link>
            </li>
            <li>
              <Link
                href="/examples"
                className="text-body hover:text-ink transition"
              >
                Examples
              </Link>
            </li>
          </ul>
        </div>
      </div>
    </footer>
  );
}
