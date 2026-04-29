import { cn } from "@/lib/cn";

type Tone = "accent" | "success" | "muted" | "coral";

const TONE_CLASS: Record<Tone, string> = {
  accent: "bg-accent-soft text-accent",
  success: "bg-success-soft text-success-ink",
  muted: "bg-canvas text-muted",
  coral: "bg-coral/15 text-ink",
};

// A small rounded pill used in headers, tiles, and the showcase header strip.
// Keeps tone semantics in one place so the same labels look identical wherever
// they appear.
export function StatPill({
  label,
  tone = "accent",
  className,
}: {
  label: string;
  tone?: Tone;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "rounded-full px-3 py-1 text-xs font-semibold inline-flex items-center",
        TONE_CLASS[tone],
        className,
      )}
    >
      {label}
    </span>
  );
}
