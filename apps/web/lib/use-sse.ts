"use client";

import { useEffect, useRef, useState } from "react";
import { type ApiMode, streamUrl } from "./api";
import type { Envelope } from "./types";

export type UseSseResult = {
  connected: boolean;
};

// One EventSource per page. The caller passes a stable `onEvent` callback
// (memoised with useCallback). Reconnection is delegated to the browser; the
// orchestrator buffers the last 2000 envelopes per sim so reopening picks up
// where we left off via Last-Event-ID. `mode` switches between live
// (`/api/sim/.../stream`) and replay (`/api/replay/.../stream`).
export function useSse(
  simId: string,
  onEvent: (env: Envelope) => void,
  mode: ApiMode = "live",
): UseSseResult {
  const [connected, setConnected] = useState(false);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  useEffect(() => {
    if (!simId) return;
    const url = streamUrl(simId, mode);
    const es = new EventSource(url);

    es.onopen = () => setConnected(true);
    es.onerror = () => setConnected(false);

    // The orchestrator's SseHub writes events as:
    //
    //   id: <seq>
    //   event: <envelope.type>
    //   data: <json of the payload>
    //
    // EventSource exposes the SSE event name as `ev.type`, the payload as
    // `ev.data`. Default `onmessage` only fires for events whose SSE name is
    // "message", so we subscribe addEventListener for every type the
    // orchestrator emits. The handler synthesises an Envelope from those two
    // pieces plus the sender id sniffed off the payload.
    const handle = (ev: MessageEvent<string>) => {
      try {
        const payload = JSON.parse(ev.data) as Record<string, unknown>;
        const type =
          ev.type === "message"
            ? String((payload.type as string | undefined) ?? "message")
            : ev.type;
        const envelope: Envelope = {
          type,
          data: payload,
          ts: new Date().toISOString(),
          from:
            (payload.sender_id as string | undefined) ??
            (payload.judge_peer_id as string | undefined) ??
            (payload.sponsor_peer_id as string | undefined) ??
            (payload.peer_id as string | undefined),
        };
        onEventRef.current(envelope);
      } catch {
        if (typeof console !== "undefined") {
          console.warn("[hacksim] dropped malformed SSE envelope");
        }
      }
    };

    es.onmessage = handle;
    // Listen for every named event the orchestrator emits. Worker-internal
    // and runtime events also flow through so the run log catches every
    // transition.
    const TYPES = [
      "sim.created",
      "sim.spawned",
      "sim.start_error",
      "organiser.scheduled",
      "phase.tick",
      "phase.tick.broadcast",
      "bounty.posted",
      "bounty.broadcast",
      "designer.composing",
      "designer.heard_prompt",
      "team.forming",
      "team.formed",
      "team.broadcast",
      "builder.registered",
      "builder.heard_bounty",
      "builder.no_bounty",
      "builder.no_team",
      "builder.building",
      "builder.build_error",
      "project.submitted",
      "project.broadcast",
      "judge.heard_project",
      "judge.no_projects",
      "rubric.published",
      "rubric.broadcast",
      "verdict.published",
      "verdict.broadcast",
      "hackathon.closed",
      "hackathon.closed.broadcast",
      "orch.registered",
      "orch.register_error",
      "worker.started",
      "worker.stopped",
      "worker.error",
      "worker.handler_error",
      "worker.gossip_error",
      "worker.skipped",
      "envelope.unhandled",
    ];
    for (const t of TYPES) {
      es.addEventListener(t, (ev) => handle(ev as MessageEvent<string>));
    }

    // Replay terminal events the orchestrator sends so the run log
    // shows the start and finish lines for a recorded run.
    for (const t of ["replay.started", "replay.finished"]) {
      es.addEventListener(t, (ev) => handle(ev as MessageEvent<string>));
    }

    return () => {
      es.close();
    };
  }, [simId, mode]);

  return { connected };
}
