"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Check, Copy } from "lucide-react";

const INSTRUCTIONS = `You are helping me run HackSim locally. HackSim is a hackathon simulator
that boots fifteen AXL Go nodes peering on loopback and runs an end-to-end
agent-driven hackathon in two to five minutes.

Do the following in order. Pause and ask me before anything that modifies my
system outside this directory.

1. Clone and enter the repo:
     git clone https://github.com/vrnvrn/hacksim
     cd hacksim

2. Confirm prerequisites are installed: Go 1.25 or newer, Node 20 or newer
   with pnpm, Python 3.10 or newer, openssl. If any are missing, tell me
   which and the install command for my OS.

3. Initialise the AXL submodule and build the Go binary:
     git submodule update --init --recursive
     make build-axl

4. Install the project git hooks:
     make hooks-install

5. Ask me whether I want to set ANTHROPIC_API_KEY before starting. Explain:
   without one, the demo runs on a deterministic stub that still produces
   real, distinct output; with one, every agent decision and every project
   HTML upgrades to a Claude haiku 4.5 call. If I say yes, walk me through
     export ANTHROPIC_API_KEY=...
   in my current shell. Do not write the key to any file.

6. Start the demo:
     make demo
   This boots the FastAPI orchestrator on :8000, the Next.js dev server on
   :3000, and opens http://localhost:3000.

7. Once the page loads, tell me to type a prompt or click an example, and
   stay available to debug if any step fails.

Repo: https://github.com/vrnvrn/hacksim
Architecture: docs/ARCHITECTURE.md
Integration test that proves AXL is on the wire:
  tests/integration/test_two_node_send.py
`;

export function AgentInstructions() {
  const [copied, setCopied] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const onCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(INSTRUCTIONS);
      setCopied(true);
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  }, []);

  return (
    <div
      className="relative rounded-2xl border border-accent/40 bg-navy-950 text-canvas overflow-hidden"
      aria-label="HackSim setup instructions, copy to share with a coding agent"
    >
      <button
        type="button"
        onClick={onCopy}
        aria-label="Copy setup instructions to clipboard"
        className="absolute top-3 right-3 z-10 inline-flex items-center gap-1.5 rounded-lg border border-accent/60 bg-navy-950/80 px-3 py-1.5 text-xs font-mono uppercase tracking-wide text-canvas hover:bg-accent/20 transition"
      >
        {copied ? (
          <Check aria-hidden className="h-3.5 w-3.5" />
        ) : (
          <Copy aria-hidden className="h-3.5 w-3.5" />
        )}
        <span>{copied ? "Copied" : "Copy"}</span>
      </button>
      <span role="status" aria-live="polite" className="sr-only">
        {copied ? "Setup instructions copied to clipboard" : ""}
      </span>
      <pre className="font-mono text-xs sm:text-sm leading-relaxed px-4 sm:px-6 py-5 pr-24 overflow-x-auto whitespace-pre">
        <code>{INSTRUCTIONS}</code>
      </pre>
    </div>
  );
}
