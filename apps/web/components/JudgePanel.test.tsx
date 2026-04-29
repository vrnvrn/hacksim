import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { JudgePanel } from "./JudgePanel";
import type { Judge } from "@/lib/types";

const judge: Judge = {
  peer_id: "c".repeat(64),
  display_name: "Vesna Pavic",
  rubric: [
    { name: "Functionality", weight: 0.5, description: "Does it work end to end." },
    { name: "Design", weight: 0.3, description: "Visual coherence." },
    { name: "Originality", weight: 0.2, description: "New angle, not a copy." },
  ],
  scored_count: 4,
  total_to_score: 8,
};

describe("JudgePanel", () => {
  it("shows the judge name and progress counter", () => {
    render(<JudgePanel judge={judge} />);
    expect(screen.getByText("Vesna Pavic")).toBeInTheDocument();
    expect(screen.getByText("scored 4 of 8")).toBeInTheDocument();
  });

  it("renders every rubric item with its weight", () => {
    render(<JudgePanel judge={judge} />);
    expect(screen.getByText("Functionality")).toBeInTheDocument();
    expect(screen.getByText("50%")).toBeInTheDocument();
    expect(screen.getByText("30%")).toBeInTheDocument();
    expect(screen.getByText("20%")).toBeInTheDocument();
  });

  it("matches the default snapshot", () => {
    const { container } = render(<JudgePanel judge={judge} />);
    expect(container.firstChild).toMatchSnapshot();
  });
});
