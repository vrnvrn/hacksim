"use client";

import { useEffect, useRef, useState } from "react";
import { streamUrl } from "./api";
import type { Envelope } from "./types";

export type UseSseResult = {
  connected: boolean;
};

// One EventSource per page. The caller passes a stable `onEvent` callback
// (memoised with useCallback). Reconnection is delegated to the browser; the
// orchestrator buffers the last 2000 envelopes per sim so reopening picks up
// where we left off via Last-Event-ID.
export function useSse(
  simId: string,
  onEvent: (env: Envelope) => void,
): UseSseResult {
  const [connected, setConnected] = useState(false);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  useEffect(() => {
    if (!simId) return;
    const url = streamUrl(simId);
    const es = new EventSource(url);

    es.onopen = () => setConnected(true);
    es.onerror = () => setConnected(false);

    const handle = (ev: MessageEvent<string>) => {
      try {
        const parsed = JSON.parse(ev.data) as Envelope;
        onEventRef.current(parsed);
      } catch {
        // Malformed envelope. Drop it; the run-log will skip a tick. The
        // backend writes one envelope per data: line, so a parse failure is
        // a real bug and surfaces in dev as a console warning.
        if (typeof console !== "undefined") {
          console.warn("[hacksim] dropped malformed SSE envelope");
        }
      }
    };

    es.onmessage = handle;
    // Backend also emits typed events; subscribe to the union.
    const TYPES = [
      "bounty.posted",
      "team.forming",
      "team.formed",
      "project.submitted",
      "rubric.published",
      "verdict.published",
      "phase.tick",
      "hackathon.closed",
    ];
    for (const t of TYPES) {
      es.addEventListener(t, (ev) => handle(ev as MessageEvent<string>));
    }

    return () => {
      es.close();
    };
  }, [simId]);

  return { connected };
}
