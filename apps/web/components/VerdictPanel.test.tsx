import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { VerdictPanel } from "./VerdictPanel";
import type { Judge, Project, Verdict } from "@/lib/types";

const project: Project = {
  id: "proj_1",
  team_id: "team_1",
  bounty_id: "bnty_1",
  title: "Permit Two-Tap",
  tagline: "",
  description: "",
  status: "judged",
  submitted_at: "2026-04-28T12:00:00Z",
  commit_hash: "deadbee",
  entry_path: "index.html",
  artefact_path: "/x",
  github_url: null,
};

const judges: Judge[] = [
  {
    peer_id: "0".repeat(64),
    display_name: "Vesna",
    rubric: [
      { name: "Functionality", weight: 0.6, description: "Works." },
      { name: "Design", weight: 0.4, description: "Pretty." },
    ],
    scored_count: 1,
    total_to_score: 1,
  },
];

const verdicts: Verdict[] = [
  {
    project_id: "proj_1",
    judge_peer_id: "0".repeat(64),
    scores: { Functionality: 8, Design: 7 },
    total: 7.6,
    feedback: "Solid demo, mobile a bit cramped.",
    interactions_summary: "click then click",
  },
];

describe("VerdictPanel", () => {
  it("renders the rubric and the per-judge accordion", () => {
    render(
      <VerdictPanel project={project} verdicts={verdicts} judges={judges} />,
    );
    expect(screen.getByText("Verdict")).toBeInTheDocument();
    expect(screen.getAllByText("Functionality").length).toBeGreaterThan(0);
    expect(screen.getByText("Vesna")).toBeInTheDocument();
  });

  it("expands to show feedback", () => {
    render(
      <VerdictPanel project={project} verdicts={verdicts} judges={judges} />,
    );
    fireEvent.click(screen.getByRole("button", { expanded: false }));
    expect(
      screen.getByText("Solid demo, mobile a bit cramped."),
    ).toBeInTheDocument();
  });

  it("shows an empty state when status is not judged", () => {
    render(
      <VerdictPanel
        project={{ ...project, status: "submitted" }}
        verdicts={[]}
        judges={judges}
      />,
    );
    expect(
      screen.getByText("This project has not been judged yet."),
    ).toBeInTheDocument();
  });

  it("matches the default snapshot", () => {
    const { container } = render(
      <VerdictPanel project={project} verdicts={verdicts} judges={judges} />,
    );
    expect(container.firstChild).toMatchSnapshot();
  });
});
