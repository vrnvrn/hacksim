"use client";

import { useState, useTransition } from "react";
import type { Project, SimConfig } from "@/lib/types";
import { ProjectTile } from "./ProjectTile";
import { getAnthropicKey, isLocalhostOrigin } from "@/lib/anthropic-key";

const DEFAULT_CONFIG: SimConfig = {
  builders: 8,
  judges: 3,
  designers: 3,
  duration_hint: "short",
  pace: "quick",
};

export function ExampleCard({
  project,
  prompt,
}: {
  project: Project;
  prompt: string;
}) {
  const [isPending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  function spinUp() {
    setError(null);
    startTransition(async () => {
      try {
        const apiKey = getAnthropicKey();
        const body: Record<string, unknown> = {
          prompt,
          config: DEFAULT_CONFIG,
        };
        if (apiKey && isLocalhostOrigin()) {
          body.anthropic_api_key = apiKey;
        }
        const res = await fetch("/api/sim", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        if (!res.ok) throw new Error(`status ${res.status}`);
        const json = (await res.json()) as { id: string };
        window.location.href = `/sim/${json.id}`;
      } catch {
        setError("Could not reach the orchestrator. Run `make demo` and retry.");
      }
    });
  }

  return (
    <div className="flex flex-col gap-2">
      <button
        type="button"
        onClick={spinUp}
        disabled={isPending}
        aria-label={`Spin up an example sim with prompt: ${prompt}`}
        className="block w-full text-left focus:outline-none focus:ring-2 focus:ring-accent rounded-3xl disabled:opacity-60 disabled:cursor-progress"
      >
        <ProjectTile project={project} showCta={false} />
      </button>
      {isPending ? (
        <p className="text-xs text-muted px-1" role="status">
          Spinning up a sim with this prompt…
        </p>
      ) : null}
      {error ? (
        <p className="text-xs text-coral px-1" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
