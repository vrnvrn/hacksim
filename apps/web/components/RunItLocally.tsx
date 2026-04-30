/**
 * RunItLocally. Static panel above the FAQ on /docs. The hosted preview
 * sends judges here from the layout-mounted banner. Tells them, in five
 * minutes flat, how to clone, build, and watch a real AXL mesh.
 *
 * No env-var gating: the panel renders on every build because the
 * quickstart is useful to local users and judges alike. Anchor id
 * "run-it-locally" matches the banner deep link.
 */
const QUICKSTART = `git clone https://github.com/vrnvrn/hacksim
cd hacksim
git submodule update --init --recursive
make build-axl
make hooks-install
make demo`;

const TIMINGS: Array<{ at: string; what: string }> = [
  { at: "t + 0 s", what: "Orchestrator on :8000, frontend on :3000, browser opens." },
  { at: "t + 3 s", what: "POST /api/sim from the hero spawns the bootstrap organiser node." },
  { at: "t + 5 s", what: "All fifteen AXL Go nodes peering through the loopback bootstrap." },
  { at: "t + 18 s", what: "phase.tick TEAM_FORMATION; builders pick a bounty." },
  { at: "t + 30 s", what: "phase.tick BUILD; builders write index.html, git commit, broadcast." },
  { at: "t + 75 s", what: "phase.tick JUDGING; judges read the artefacts and score." },
  { at: "t + 110 s", what: "hackathon.closed; click any winner card to play with the artefact." },
];

const VERIFY = `# 1) Run the integration test that boots two real AXL Go binaries.
pytest tests/integration/test_two_node_send.py -q

# 2) During make demo, watch loopback traffic to AXL on 127.0.0.1.
sudo tcpdump -i lo0 -n 'tcp port 9100' | head -20

# 3) See the fifteen AXL processes the orchestrator spawned.
ps aux | grep third_party/axl/node | grep -v grep`;

export function RunItLocally() {
  return (
    <section
      id="run-it-locally"
      aria-labelledby="run-it-locally-heading"
      className="mt-12 rounded-3xl border border-accent/40 bg-accent/5 p-6 lg:p-8"
    >
      <p className="text-xs font-mono uppercase tracking-[0.18em] text-accent">
        [ run it locally ]
      </p>
      <h2
        id="run-it-locally-heading"
        className="font-display text-2xl lg:text-3xl font-semibold text-ink mt-2"
      >
        Five minutes from clone to a live AXL mesh
      </h2>
      <p className="text-body mt-3 max-w-3xl leading-relaxed">
        The hosted preview replays a recorded run. The canonical demo runs
        on your machine: one organiser, three bounty designers, eight
        builders, and three judges, all peering through Yggdrasil on
        loopback. Every cross-agent byte goes through AXL.
      </p>

      <h3 className="font-display text-lg font-semibold text-ink mt-6">
        Quickstart
      </h3>
      <p className="text-sm text-body mt-2">
        Prereqs: Go 1.25 or newer, Node 20 with{" "}
        <code className="rounded bg-canvas px-1.5 py-0.5 font-mono text-[0.85em] text-ink">
          pnpm
        </code>
        , Python 3.10+, openssl. No accounts, no API keys required (the
        deterministic stub produces real, distinct output without
        ANTHROPIC_API_KEY set).
      </p>
      <pre className="mt-3 rounded-xl bg-navy-950 text-canvas font-mono text-xs px-4 py-3 overflow-x-auto leading-relaxed">
        <code>{QUICKSTART}</code>
      </pre>

      <h3 className="font-display text-lg font-semibold text-ink mt-6">
        What you should see
      </h3>
      <p className="text-sm text-body mt-2">
        Quick pace (the default). Browser pops automatically.
      </p>
      <ul className="mt-3 space-y-2">
        {TIMINGS.map((t) => (
          <li
            key={t.at}
            className="flex items-baseline gap-3 text-sm leading-relaxed"
          >
            <span className="font-mono text-xs text-accent shrink-0 w-16">
              {t.at}
            </span>
            <span className="text-body">{t.what}</span>
          </li>
        ))}
      </ul>

      <h3 className="font-display text-lg font-semibold text-ink mt-6">
        Verify the qualification gate yourself
      </h3>
      <p className="text-sm text-body mt-2">
        AXL bounty rules require communication across separate AXL nodes.
        The integration test boots two real binaries and asserts a
        cross-node send; the tcpdump confirms the loopback bootstrap is
        the only wire; the process list shows fifteen distinct
        node binaries during a sim.
      </p>
      <pre className="mt-3 rounded-xl bg-navy-950 text-canvas font-mono text-xs px-4 py-3 overflow-x-auto leading-relaxed">
        <code>{VERIFY}</code>
      </pre>

      <p className="text-xs text-muted mt-6 leading-relaxed">
        The chronological build is readable in fifteen minutes under{" "}
        <a
          href="https://github.com/vrnvrn/hacksim/tree/main/docs/process"
          target="_blank"
          rel="noreferrer"
          className="text-accent hover:underline"
        >
          docs/process/
        </a>{" "}
        and the architecture diagram lives in{" "}
        <a
          href="https://github.com/vrnvrn/hacksim/blob/main/docs/ARCHITECTURE.md"
          target="_blank"
          rel="noreferrer"
          className="text-accent hover:underline"
        >
          docs/ARCHITECTURE.md
        </a>
        .
      </p>
    </section>
  );
}
