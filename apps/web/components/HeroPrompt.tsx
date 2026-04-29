"use client";

import { useState, useTransition, type FormEvent, type KeyboardEvent } from "react";
import { Settings2 } from "lucide-react";
import * as Popover from "@radix-ui/react-popover";
import type { SimConfig } from "@/lib/types";
import { cn } from "@/lib/cn";

const DEFAULT_CONFIG: SimConfig = {
  builders: 8,
  judges: 3,
  designers: 3,
  duration_hint: "short",
};

const SMALL_MODE: SimConfig = {
  builders: 3,
  judges: 1,
  designers: 1,
  duration_hint: "short",
};

const PLACEHOLDER =
  "an onchain agents hackathon with five sponsors and a $5k pool";

const EXAMPLE_SIM_ID = "sim_2026-04-28_a1b2c3";

export function HeroPrompt({
  onSubmit,
  exampleHref = `/sim/${EXAMPLE_SIM_ID}`,
}: {
  onSubmit?: (prompt: string, cfg: SimConfig) => void;
  exampleHref?: string;
}) {
  const [prompt, setPrompt] = useState("");
  const [config, setConfig] = useState<SimConfig>(DEFAULT_CONFIG);
  const [isPending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  function handleSubmit(e?: FormEvent) {
    e?.preventDefault();
    const trimmed = prompt.trim();
    if (!trimmed) {
      setError("Add a prompt to spin up a sim.");
      return;
    }
    setError(null);
    if (onSubmit) {
      onSubmit(trimmed, config);
      return;
    }
    startTransition(async () => {
      try {
        const res = await fetch("/api/sim", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt: trimmed, config }),
        });
        if (!res.ok) throw new Error(`status ${res.status}`);
        const json = (await res.json()) as { id: string };
        window.location.href = `/sim/${json.id}`;
      } catch {
        setError("Could not reach the orchestrator. Mock mode keeps the UI working; flip NEXT_PUBLIC_USE_MOCKS=true.");
      }
    });
  }

  function handleKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }

  return (
    <form onSubmit={handleSubmit} className="mt-12 max-w-3xl">
      <label htmlFor="hero-prompt" className="visually-hidden">
        Describe the hackathon you want
      </label>
      <textarea
        id="hero-prompt"
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        onKeyDown={handleKey}
        placeholder={PLACEHOLDER}
        className="w-full rounded-3xl border border-border focus:border-accent focus:outline-none p-6 text-lg min-h-[140px] shadow-sm bg-surface text-ink placeholder:text-muted resize-vertical"
        aria-describedby={error ? "hero-prompt-error" : undefined}
      />
      {error ? (
        <p id="hero-prompt-error" role="alert" className="text-sm text-coral mt-2">
          {error}
        </p>
      ) : null}
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <button
          type="submit"
          disabled={isPending}
          className={cn(
            "rounded-md px-6 py-3 bg-accent text-white font-semibold hover:opacity-90 transition disabled:opacity-50",
          )}
        >
          {isPending ? "Spinning up..." : "Spin up sim"}
        </button>
        <a
          href={exampleHref}
          className="rounded-full border-2 border-ink bg-surface text-ink px-6 py-3 font-semibold hover:bg-ink hover:text-surface transition"
        >
          See an example run
        </a>
        <SettingsPopover config={config} onChange={setConfig} />
      </div>
    </form>
  );
}

function SettingsPopover({
  config,
  onChange,
}: {
  config: SimConfig;
  onChange: (cfg: SimConfig) => void;
}) {
  return (
    <Popover.Root>
      <Popover.Trigger asChild>
        <button
          type="button"
          className="inline-flex items-center gap-2 text-sm font-medium text-body hover:text-ink transition"
          aria-label="Open simulation settings"
        >
          <Settings2 className="h-4 w-4" aria-hidden="true" />
          Settings
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          align="start"
          sideOffset={8}
          className="z-40 w-80 rounded-2xl border border-border bg-surface p-5 shadow-lg"
        >
          <h3 className="font-display text-lg font-semibold text-ink">
            Simulation settings
          </h3>
          <p className="text-xs text-muted mt-1">
            Override agent counts. Defaults work for a five-minute demo.
          </p>
          <div className="mt-4 space-y-4">
            <SliderRow
              label="Builders"
              value={config.builders}
              min={2}
              max={20}
              onChange={(builders) => onChange({ ...config, builders })}
            />
            <SliderRow
              label="Judges"
              value={config.judges}
              min={1}
              max={9}
              onChange={(judges) => onChange({ ...config, judges })}
            />
            <SliderRow
              label="Bounty designers"
              value={config.designers}
              min={1}
              max={9}
              onChange={(designers) => onChange({ ...config, designers })}
            />
          </div>
          <div className="mt-5 flex items-center justify-between border-t border-border pt-4">
            <button
              type="button"
              onClick={() =>
                onChange({
                  builders: SMALL_MODE.builders,
                  judges: SMALL_MODE.judges,
                  designers: SMALL_MODE.designers,
                  duration_hint: SMALL_MODE.duration_hint,
                })
              }
              className="rounded-full border border-border px-3 py-1 text-xs font-medium text-body hover:bg-canvas transition"
            >
              Small mode (3, 1, 1)
            </button>
            <Popover.Close
              className="text-xs font-medium text-accent hover:underline"
              aria-label="Close settings"
            >
              Done
            </Popover.Close>
          </div>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}

function SliderRow({
  label,
  value,
  min,
  max,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  onChange: (v: number) => void;
}) {
  const id = `slider-${label.toLowerCase().replace(/\s+/g, "-")}`;
  return (
    <div>
      <div className="flex items-center justify-between">
        <label htmlFor={id} className="text-sm font-medium text-ink">
          {label}
        </label>
        <span className="text-sm font-mono tabular-nums text-body">
          {value}
        </span>
      </div>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="mt-2 w-full accent-accent"
      />
    </div>
  );
}
