// Data shapes for the HackSim frontend. The contract lives in
// refs/UX_SPEC.md section 7. The backend FastAPI app emits these shapes byte
// for byte; if anything drifts the spec is wrong and we update it.

export type PeerId = string; // 64 hex chars

export type SimConfig = {
  builders: number;
  judges: number;
  designers: number;
  duration_hint: "short" | "medium" | "long";
};

export type Bounty = {
  id: string;
  title: string;
  sponsor_name: string;
  sponsor_peer_id: PeerId;
  prize_amount_usd: number;
  description: string;
  qualification: string[];
  created_at: string;
};

export type Builder = {
  peer_id: PeerId;
  display_name: string;
  skills: string[];
  team_id: string | null;
  current_bounty_id: string | null;
  persona_excerpt?: string;
};

export type Team = {
  id: string;
  bounty_id: string;
  members: PeerId[];
  formed_at: string;
};

export type ProjectStatus = "drafting" | "submitted" | "judged";

export type Project = {
  id: string;
  team_id: string;
  bounty_id: string;
  title: string;
  tagline: string;
  description: string;
  status: ProjectStatus;
  submitted_at: string | null;
  commit_hash: string | null;
  entry_path: string | null;
  artefact_path: string | null;
  github_url: string | null;
};

export type ProjectFile = {
  path: string;
  size_bytes: number;
  kind: "text" | "image" | "binary";
};

export type RubricCriterion = {
  name: string;
  weight: number;
  description: string;
};

export type Judge = {
  peer_id: PeerId;
  display_name: string;
  rubric: RubricCriterion[];
  scored_count: number;
  total_to_score: number;
};

export type Verdict = {
  project_id: string;
  judge_peer_id: PeerId;
  scores: Record<string, number>;
  total: number;
  feedback: string;
  interactions_summary?: string;
};

export type Phase = 0 | 1 | 2 | 3 | 4;

export const PHASE_LABELS: Record<Phase, string> = {
  0: "queued",
  1: "designing",
  2: "building",
  3: "judging",
  4: "closed",
};

export type Snapshot = {
  id: string;
  prompt: string;
  config: SimConfig;
  phase: Phase;
  created_at: string;
  bounties: Bounty[];
  builders: Builder[];
  teams: Team[];
  projects: Project[];
  judges: Judge[];
  verdicts: Verdict[];
};

export type Envelope = {
  type: string;
  data: Record<string, unknown>;
  ts?: string;
  from?: PeerId;
};
