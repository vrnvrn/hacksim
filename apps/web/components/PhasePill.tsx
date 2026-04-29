import { PHASE_LABELS, type Phase } from "@/lib/types";
import { StatPill } from "./StatPill";

// Live phase indicator. The visible pill is colour-coded per phase. A
// screen-reader sibling spells the phase out so users who do not see colour
// still know where the sim is.
const TONE_BY_PHASE: Record<Phase, "muted" | "accent" | "success"> = {
  0: "muted",
  1: "accent",
  2: "accent",
  3: "accent",
  4: "success",
};

export function PhasePill({ phase }: { phase: Phase }) {
  const label = PHASE_LABELS[phase];
  const tone = TONE_BY_PHASE[phase];
  return (
    <span aria-label={`Current phase, ${label}`} className="inline-flex">
      <StatPill label={`Phase: ${label}`} tone={tone} />
      <span className="visually-hidden">{`Current phase: ${label}`}</span>
    </span>
  );
}
