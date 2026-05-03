"use client";

import { useState, useTransition } from "react";
import { RotateCcw } from "lucide-react";

// Calls POST /api/sim/reset and redirects to /. The endpoint stops every
// running sim and frees the loopback bootstrap port. Used when a sim
// wedges (designer workers crashed, AXL nodes stuck on 127.0.0.1:9100)
// so a judge mid-demo can recover from the browser.

export function RestartSimButton({
  className,
}: {
  className?: string;
}) {
  const [isPending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  function handleClick() {
    if (
      typeof window !== "undefined" &&
      !window.confirm(
        "Stop this simulation and every other running sim, then return to the home page?",
      )
    ) {
      return;
    }
    setError(null);
    startTransition(async () => {
      try {
        const res = await fetch("/api/sim/reset", { method: "POST" });
        if (!res.ok && res.status !== 204) {
          throw new Error(`reset returned ${res.status}`);
        }
        window.location.href = "/";
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        setError(`Restart failed: ${msg}`);
      }
    });
  }

  return (
    <span className="inline-flex items-center gap-2">
      <button
        type="button"
        onClick={handleClick}
        disabled={isPending}
        aria-label="Restart simulation"
        className={
          className ??
          "inline-flex items-center gap-1.5 rounded-md border border-border bg-surface px-3 py-1.5 text-xs font-medium text-body hover:bg-canvas hover:text-ink transition disabled:opacity-50"
        }
      >
        <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
        {isPending ? "Restarting..." : "Restart simulation"}
      </button>
      {error ? (
        <span role="alert" className="text-xs text-coral">
          {error}
        </span>
      ) : null}
    </span>
  );
}
