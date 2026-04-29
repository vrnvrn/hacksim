/**
 * Plain-text FAQ for /docs. Server-rendered, native <details> accordions.
 *
 * Audience: ETHGlobal Open Agents 2026 reviewers, Gensyn AXL judges who
 * want to verify the qualification gate, and curious users who want to
 * know what is real and what is a fixture before they hit Spin up sim.
 */

type Faq = {
  q: string;
  a: React.ReactNode;
};

const ITEMS: Faq[] = [
  {
    q: "What AI are the agents using?",
    a: (
      <>
        <P>
          Anthropic <Code>claude-haiku-4-5-20251001</Code> via the official
          Python SDK. Optional. Triggered when{" "}
          <Code>ANTHROPIC_API_KEY</Code> is set in the shell that runs{" "}
          <Code>make demo</Code>. Four call sites, one per role decision:
        </P>
        <Ul>
          <li>
            Bounty designers compose each bounty (
            <Code>packages/agents/bounty_designer/decisions.py</Code>).
          </li>
          <li>
            Builders pick the bounty that fits their skills, then write the
            project HTML (
            <Code>packages/agents/builder/decisions.py</Code> and{" "}
            <Code>builder/build.py</Code>).
          </li>
          <li>
            Judges score every submission with feedback (
            <Code>packages/agents/judge/decisions.py</Code>).
          </li>
        </Ul>
        <P>
          Without a key, every call falls back to a deterministic stub keyed
          off the agent&rsquo;s peer id and the prompt hash. The stubs still
          produce real output (a working interactive canvas, plausible
          bounty text, sensible scores), just template-authored instead of
          LLM-authored. That fallback is what lets the demo run for a
          reviewer who has not set a key. We do not use Claude Code in the
          running demo.
        </P>
      </>
    ),
  },
  {
    q: "How does HackSim use Gensyn AXL?",
    a: (
      <>
        <P>
          AXL is the wire between agents. The orchestrator spawns one AXL Go
          binary per role node (15 nodes by default: one organiser, three
          sponsors, eight builders, three judges). Each node has its own
          ed25519 keypair and its own ports. They peer through a single TLS
          bootstrap on <Code>127.0.0.1:9100</Code>.
        </P>
        <P>Four AXL HTTP surfaces exercised by the running sim:</P>
        <Ul>
          <li>
            <Code>GET /topology</Code> for peer discovery (the algorithm is
            ported from Gensyn&rsquo;s autoresearch demo).
          </li>
          <li>
            <Code>POST /send</Code> for broadcast (bounty.posted,
            team.formed, project.submitted, verdict.published, phase.tick).
          </li>
          <li>
            <Code>GET /recv</Code> to drain inbound envelopes from each
            role&rsquo;s queue.
          </li>
          <li>
            <Code>POST /mcp/{`{peer}`}/{`{service}`}</Code> for typed
            JSON-RPC across the mesh, used when builders call a
            judge&rsquo;s <Code>score</Code> tool over Yggdrasil.
          </li>
        </Ul>
        <P>
          Every cross-agent message travels through the Yggdrasil mesh AXL
          builds on top of. The orchestrator only spawns processes and
          serves the UI; it never relays agent traffic. Removing AXL
          silences the simulation.
        </P>
      </>
    ),
  },
  {
    q: "How is HackSim different from Gensyn's autoresearch demo?",
    a: (
      <>
        <P>
          Same transport (AXL), different shape. The autoresearch demo is a
          flat topology where identical agents broadcast findings on one
          envelope type and adopt each other&rsquo;s improvements. HackSim
          has four typed roles in a phased lifecycle (bounty design, team
          formation, build, judging, showcase), eight envelope types, and
          uses the <Code>/mcp/{`{peer}`}/{`{service}`}</Code> surface for
          typed addressed calls between roles. The autoresearch demo does
          not exercise <Code>/mcp</Code>. We borrow the broadcast loop and
          the topology dedup pattern verbatim from{" "}
          <Code>research_network.py</Code>; the rest is HackSim.
        </P>
      </>
    ),
  },
  {
    q: "Do I need an Anthropic API key?",
    a: (
      <>
        <P>
          No. <Code>make demo</Code> works with no key set; every agent
          call falls back to a deterministic stub. With a key set, every
          decision and every project&rsquo;s HTML upgrades to a Claude
          haiku 4.5 call. Either way, the AXL mesh, the cross-agent
          envelopes, and the artefact pipeline are real.
        </P>
      </>
    ),
  },
  {
    q: "How long does a sim take?",
    a: (
      <>
        <P>
          Pace presets in the SimConfig set the phase schedule. Defaults
          are tuned for a watchable demo:
        </P>
        <Ul>
          <li>
            <Code>smoke</Code>: 75 seconds end to end (used by the
            headless test harness).
          </li>
          <li>
            <Code>quick</Code> (default for <Code>make demo</Code>): 110
            seconds.
          </li>
          <li>
            <Code>medium</Code>: 5-6 minutes.
          </li>
          <li>
            <Code>deep</Code>: 12 minutes.
          </li>
        </Ul>
        <P>
          The Settings popover under the hero prompt caps agent counts
          (builders 1-10, judges 1-5, designers 1-5) so the loopback
          mesh stays watchable.
        </P>
      </>
    ),
  },
  {
    q: "Are the projects the agents build real, runnable code?",
    a: (
      <>
        <P>
          Yes. Each builder writes a real{" "}
          <Code>index.html</Code> plus <Code>app.js</Code> plus{" "}
          <Code>style.css</Code> into its own working directory, runs{" "}
          <Code>git init &amp;&amp; git add &amp;&amp; git commit</Code>,
          then broadcasts <Code>project.submitted</Code> with the commit
          hash. The orchestrator runs:
        </P>
        <Pre>{`git archive --format=tar <commit_hash> | tar -x -C sim-runs/<sim_id>/projects/<project_id>/`}</Pre>
        <P>
          The Demo tab in the showcase modal points an iframe at that
          tree. The Code tab uses{" "}
          <Code>shiki.codeToHtml</Code> on the real file contents.
          Click any winner card and switch tabs to see the source the
          agents wrote, byte for byte.
        </P>
      </>
    ),
  },
  {
    q: "Is it safe to render agent-written code in my browser?",
    a: (
      <>
        <P>The artefact static route serves with this CSP:</P>
        <Pre>{`Content-Security-Policy:
  default-src 'none';
  script-src 'self' 'unsafe-inline';
  style-src 'self' 'unsafe-inline';
  img-src 'self' data:;
  font-src 'self' data:;
  frame-ancestors 'self'`}</Pre>
        <P>
          The iframe in the modal sets{" "}
          <Code>sandbox=&quot;allow-scripts&quot;</Code> only (no
          allow-same-origin, no allow-top-navigation, no allow-forms, no
          allow-popups). Agent code can run script and styles but cannot
          fetch, navigate, set cookies, or read parent state.
        </P>
      </>
    ),
  },
  {
    q: "Is the AXL qualification gate satisfied?",
    a: (
      <>
        <P>
          The rules require &ldquo;communication across separate AXL
          nodes, not in-process.&rdquo; Every agent role runs its own AXL
          Go binary built from the upstream{" "}
          <A href="https://github.com/gensyn-ai/axl">gensyn-ai/axl</A>{" "}
          submodule, with its own ed25519 identity and its own ports. No
          process holds two roles. There is no central message broker.
          Cross-agent messages travel through the Yggdrasil mesh AXL
          provides.
        </P>
      </>
    ),
  },
  {
    q: "How do I verify every cross-agent byte goes through AXL?",
    a: (
      <>
        <P>While a sim is running:</P>
        <Pre>{`# 1) See the AXL Go binaries running (one per role).
ps aux | grep third_party/axl/node | grep -v grep

# 2) See each role's listening ports.
lsof -i -P -n | grep -E "node.*LISTEN" | sort

# 3) Watch loopback traffic during a run.
sudo tcpdump -i lo0 -n 'tcp port 9100 or tcp port 7000' | head -20`}</Pre>
        <P>
          Stopping every node interrupts the simulation immediately:
          designers stop posting, builders stop hearing bounties, judges
          stop scoring. The AXL nodes are the system&rsquo;s nervous
          system; the orchestrator is just the host.
        </P>
      </>
    ),
  },
  {
    q: "Was this built during the hackathon?",
    a: (
      <>
        <P>
          Yes. ETHGlobal Open Agents 2026, for the Best Application of the
          Agent eXchange Layer (AXL) bounty. 35+ commits, each with a
          matching process note under <Code>docs/process/</Code>. The
          chronological build is readable in roughly fifteen minutes.
          Source at{" "}
          <A href="https://github.com/vrnvrn/hacksim">
            github.com/vrnvrn/hacksim
          </A>
          .
        </P>
      </>
    ),
  },
];

export function Faq() {
  return (
    <section
      aria-labelledby="faq-heading"
      className="mt-16 rounded-3xl border border-border bg-surface p-8"
    >
      <p className="text-xs font-mono uppercase tracking-[0.18em] text-accent">
        [ faq ]
      </p>
      <h2
        id="faq-heading"
        className="font-display text-3xl font-semibold text-ink mt-2"
      >
        Frequently asked
      </h2>
      <p className="text-body mt-3 max-w-3xl leading-relaxed">
        Answers a Gensyn judge, an ETHGlobal reviewer, or a curious user is
        likely to want before reading any code.
      </p>
      <div className="mt-8 divide-y divide-border">
        {ITEMS.map((item) => (
          <details key={item.q} className="group py-4">
            <summary className="cursor-pointer list-none flex items-baseline justify-between gap-4 hover:text-ink transition">
              <span className="font-display text-lg font-semibold text-ink">
                {item.q}
              </span>
              <span
                aria-hidden="true"
                className="font-mono text-sm text-muted shrink-0 group-open:rotate-90 transition-transform"
              >
                &gt;
              </span>
            </summary>
            <div className="mt-3 space-y-3 text-body leading-relaxed max-w-3xl">
              {item.a}
            </div>
          </details>
        ))}
      </div>
    </section>
  );
}

function P({ children }: { children: React.ReactNode }) {
  return <p className="leading-relaxed">{children}</p>;
}

function Ul({ children }: { children: React.ReactNode }) {
  return <ul className="ml-5 list-disc space-y-1 leading-relaxed">{children}</ul>;
}

function Code({ children }: { children: React.ReactNode }) {
  return (
    <code className="rounded bg-canvas px-1.5 py-0.5 font-mono text-[0.85em] text-ink">
      {children}
    </code>
  );
}

function Pre({ children }: { children: string }) {
  return (
    <pre className="rounded-xl bg-navy-950 text-canvas font-mono text-xs px-4 py-3 overflow-x-auto leading-relaxed">
      <code>{children}</code>
    </pre>
  );
}

function A({
  href,
  children,
}: {
  href: string;
  children: React.ReactNode;
}) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="text-accent hover:underline"
    >
      {children}
    </a>
  );
}
