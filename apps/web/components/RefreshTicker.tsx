"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/**
 * Re-runs the parent Server Component on a regular cadence so the snapshot
 * stays in sync with the orchestrator while a sim is in progress. Stops once
 * the sim closes (`activeUntilPhase` reached).
 *
 * router.refresh() re-fetches Server Component data without a full page
 * navigation; React reconciles the new HTML against the live DOM. Cheap, and
 * it keeps the page Server-rendered for SEO and the initial paint.
 */
export function RefreshTicker({
  initialPhase,
  activeUntilPhase = 4,
  intervalMs = 2500,
}: {
  initialPhase: number;
  activeUntilPhase?: number;
  intervalMs?: number;
}) {
  const router = useRouter();
  useEffect(() => {
    if (initialPhase >= activeUntilPhase) {
      return;
    }
    const id = window.setInterval(() => {
      router.refresh();
    }, intervalMs);
    return () => window.clearInterval(id);
  }, [router, initialPhase, activeUntilPhase, intervalMs]);
  return null;
}
