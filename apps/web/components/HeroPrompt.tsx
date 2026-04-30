"use client";

import { useEffect, useState, useTransition, type FormEvent, type KeyboardEvent } from "react";
import { Settings2 } from "lucide-react";
import * as Popover from "@radix-ui/react-popover";
import type { SimConfig } from "@/lib/types";
import { cn } from "@/lib/cn";
import {
  getAnthropicKey,
  setAnthropicKey,
  isLocalhostOrigin,
} from "@/lib/anthropic-key";

const DEFAULT_CONFIG: SimConfig = {
  builders: 8,
  judges: 3,
  designers: 3,
  duration_hint: "short",
  pace: "quick",
};

const SMALL_MODE: SimConfig = {
  builders: 3,
  judges: 1,
  designers: 1,
  duration_hint: "short",
  pace: "quick",
};

const PACE_PRESETS: Array<{
  value: NonNullable<SimConfig["pace"]>;
  label: string;
  hint: string;
}> = [
  { value: "smoke", label: "Smoke", hint: "75s, headless harness" },
  { value: "quick", label: "Quick", hint: "110s, watchable demo" },
  { value: "medium", label: "Medium", hint: "5 to 6 minutes" },
  { value: "deep", label: "Deep", hint: "12 minutes" },
];

const PLACEHOLDER =
  "an onchain agents hackathon with five sponsors and a $5k pool";

export function HeroPrompt({
  onSubmit,
  exampleHref = "/examples",
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
        const apiKey = getAnthropicKey();
        const body: Record<string, unknown> = { prompt: trimmed, config };
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
    <form onSubmit={handleSubmit} className="mt-6 lg:mt-8">
      <label htmlFor="hero-prompt" className="visually-hidden">
        Describe the hackathon you want
      </label>
      <textarea
        id="hero-prompt"
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        onKeyDown={handleKey}
        placeholder={PLACEHOLDER}
        rows={3}
        className="w-full rounded-2xl border border-border focus:border-accent focus:outline-none p-4 text-base min-h-[100px] shadow-sm bg-surface text-ink placeholder:text-muted resize-vertical"
        aria-describedby={error ? "hero-prompt-error" : undefined}
      />
      {error ? (
        <p id="hero-prompt-error" role="alert" className="text-sm text-coral mt-2">
          {error}
        </p>
      ) : null}
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <button
          type="submit"
          disabled={isPending}
          className={cn(
            "inline-flex items-center gap-2 rounded-md px-5 py-2.5 bg-accent text-white text-sm font-semibold hover:opacity-90 transition disabled:opacity-50",
          )}
        >
          {isPending ? (
            <>
              <span
                aria-hidden="true"
                className="inline-block h-3 w-3 rounded-full border-2 border-white/40 border-t-white animate-spin"
              />
              Spinning up 15 AXL nodes...
            </>
          ) : (
            "Spin up sim"
          )}
        </button>
        {isPending ? (
          <span className="text-xs text-muted">about 10 seconds</span>
        ) : null}
        <a
          href={exampleHref}
          className="rounded-full border-2 border-ink bg-surface text-ink px-5 py-2.5 text-sm font-semibold hover:bg-ink hover:text-surface transition"
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
              max={10}
              onChange={(builders) => onChange({ ...config, builders })}
            />
            <SliderRow
              label="Judges"
              value={config.judges}
              min={1}
              max={5}
              onChange={(judges) => onChange({ ...config, judges })}
            />
            <SliderRow
              label="Bounty designers"
              value={config.designers}
              min={1}
              max={5}
              onChange={(designers) => onChange({ ...config, designers })}
            />
          </div>
          <p className="text-[11px] text-muted mt-3 leading-relaxed">
            Counts are capped so the loopback mesh stays watchable. Bigger
            sims need a real multi-host bootstrap.
          </p>
          <PaceRow
            value={config.pace ?? "quick"}
            onChange={(pace) => onChange({ ...config, pace })}
          />
          <KeyRow />
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
              aria-label="Use light mode (3 builders, 1 judge, 1 designer)"
            >
              Light mode (faster, fewer agents)
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

function KeyRow() {
  // Render only when the page itself is being served from localhost. The
  // orchestrator independently refuses the field with 403 from any other
  // origin, but hiding the input on a hosted page keeps a remote user
  // from ever pasting a key into a non-trusted surface.
  const [isLocal, setIsLocal] = useState(false);
  const [value, setValue] = useState("");
  const [revealed, setRevealed] = useState(false);

  useEffect(() => {
    setIsLocal(isLocalhostOrigin());
    setValue(getAnthropicKey());
  }, []);

  function onChange(next: string) {
    setValue(next);
    setAnthropicKey(next);
  }

  if (!isLocal) return null;
  return (
    <div className="mt-5 border-t border-border pt-4">
      <label
        htmlFor="anthropic-key"
        className="text-sm font-medium text-ink flex items-center justify-between"
      >
        <span>Anthropic API key</span>
        <span className="text-[10px] uppercase tracking-wider font-mono text-muted">
          local only
        </span>
      </label>
      <p className="text-[11px] text-muted mt-1 leading-relaxed">
        Optional. With a key set, role workers call Claude haiku 4.5
        instead of the deterministic stub. The key never leaves your
        machine: it rides one POST and is dropped from logs and the SSE
        buffer.
      </p>
      <div className="mt-2 flex items-center gap-2">
        <input
          id="anthropic-key"
          type={revealed ? "text" : "password"}
          autoComplete="off"
          spellCheck={false}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="sk-ant-..."
          className="flex-1 min-w-0 rounded-md border border-border bg-canvas/40 px-2 py-1.5 text-sm font-mono text-ink placeholder:text-muted focus:outline-none focus:border-accent"
        />
        <button
          type="button"
          onClick={() => setRevealed((r) => !r)}
          className="rounded-md border border-border px-2 py-1.5 text-[11px] font-medium text-body hover:bg-canvas transition"
          aria-label={revealed ? "Hide key" : "Show key"}
        >
          {revealed ? "Hide" : "Show"}
        </button>
      </div>
      {value ? (
        <button
          type="button"
          onClick={() => onChange("")}
          className="mt-2 text-[11px] text-muted hover:text-ink underline transition"
        >
          Clear key
        </button>
      ) : null}
    </div>
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

function PaceRow({
  value,
  onChange,
}: {
  value: NonNullable<SimConfig["pace"]>;
  onChange: (pace: NonNullable<SimConfig["pace"]>) => void;
}) {
  const active = PACE_PRESETS.find((p) => p.value === value) ?? PACE_PRESETS[1];
  return (
    <div className="mt-5 border-t border-border pt-4">
      <label className="text-sm font-medium text-ink flex items-center justify-between">
        <span>Pace</span>
        <span className="text-[10px] uppercase tracking-wider font-mono text-muted">
          {active.hint}
        </span>
      </label>
      <div
        role="radiogroup"
        aria-label="Simulation pace"
        className="mt-2 grid grid-cols-4 gap-1 rounded-md border border-border p-1 bg-canvas/40"
      >
        {PACE_PRESETS.map((p) => (
          <button
            key={p.value}
            type="button"
            role="radio"
            aria-checked={p.value === value}
            onClick={() => onChange(p.value)}
            className={cn(
              "rounded px-2 py-1.5 text-xs font-medium transition",
              p.value === value
                ? "bg-accent text-white"
                : "text-body hover:bg-surface",
            )}
          >
            {p.label}
          </button>
        ))}
      </div>
    </div>
  );
}
