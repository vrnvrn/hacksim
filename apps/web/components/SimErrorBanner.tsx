"use client";

import { useCallback, useState } from "react";
import { useSse } from "@/lib/use-sse";
import type { Envelope } from "@/lib/types";

/**
 * Listens to the sim's SSE stream and surfaces sim.start_error events as a
 * top-of-page coral banner. The orchestrator publishes the event when
 * SimController.start raises (AXL binary missing, port collision, key file
 * unreadable). Without this banner the live page renders an empty snapshot
 * and the user has no idea what went wrong.
 */
export function SimErrorBanner({ simId }: { simId: string }) {
  const [error, setError] = useState<string | null>(null);

  const onEvent = useCallback((env: Envelope) => {
    if (env.type === "sim.start_error") {
      const data = env.data ?? {};
      const message =
        typeof data.error === "string" && data.error.length > 0
          ? data.error
          : "The orchestrator failed to spawn the simulation.";
      setError(message);
    }
  }, []);

  useSse(simId, onEvent);

  if (!error) return null;
  return (
    <aside
      role="alert"
      aria-label="Simulation start error"
      className="border-b border-coral bg-coral/10"
    >
      <div className="max-w-7xl mx-auto px-6 lg:px-8 py-3 text-sm text-ink flex flex-wrap items-start gap-x-4 gap-y-2">
        <span className="text-[11px] font-mono uppercase tracking-[0.18em] text-coral shrink-0 mt-0.5">
          [ sim start failed ]
        </span>
        <span className="leading-relaxed flex-1 min-w-0">
          {error}
          {" "}
          The most common causes are an unbuilt AXL binary, a port already
          held by another process, or a previous demo that did not stop
          cleanly. Run{" "}
          <code className="rounded bg-canvas px-1.5 py-0.5 font-mono text-[0.85em]">
            make build-axl
          </code>{" "}
          and retry.
        </span>
        <a
          href="/"
          className="text-xs font-medium text-accent hover:underline shrink-0"
        >
          Start over &rarr;
        </a>
      </div>
    </aside>
  );
}
