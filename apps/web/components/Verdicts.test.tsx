import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Verdicts } from "./Verdicts";
import type { Verdict } from "@/lib/types";

const verdicts: Verdict[] = [
  {
    project_id: "proj_1",
    judge_peer_id: "0".repeat(64),
    scores: { Functionality: 8, Design: 7 },
    total: 7.5,
    feedback: "Solid.",
  },
  {
    project_id: "proj_2",
    judge_peer_id: "1".repeat(64),
    scores: { Functionality: 6, Design: 6 },
    total: 6,
    feedback: "Okay.",
  },
];

describe("Verdicts", () => {
  it("renders one row per project, sorted by average", () => {
    render(<Verdicts verdicts={verdicts} />);
    expect(screen.getByText("proj_1")).toBeInTheDocument();
    expect(screen.getByText("proj_2")).toBeInTheDocument();
    const rows = screen.getAllByRole("row");
    // Header + 2 data rows.
    expect(rows.length).toBe(3);
  });

  it("shows an empty message when there are no verdicts", () => {
    render(<Verdicts verdicts={[]} />);
    expect(screen.getByText(/no verdicts yet/i)).toBeInTheDocument();
  });

  it("matches the default snapshot", () => {
    const { container } = render(<Verdicts verdicts={verdicts} />);
    expect(container.firstChild).toMatchSnapshot();
  });
});
