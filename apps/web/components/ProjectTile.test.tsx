import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ProjectTile } from "./ProjectTile";
import type { Project } from "@/lib/types";

const submitted: Project = {
  id: "proj_1",
  team_id: "team_1",
  bounty_id: "bnty_1",
  title: "Permit Two-Tap",
  tagline: "Two taps from idle to signed permit.",
  description: "A tiny demo where the user taps to approve and taps to send.",
  status: "submitted",
  submitted_at: "2026-04-28T12:00:00Z",
  commit_hash: "7f3a2c9deadbeef",
  entry_path: "index.html",
  artefact_path: "/served/path",
  github_url: null,
};

describe("ProjectTile", () => {
  it("renders title, tagline and Submitted badge", () => {
    render(<ProjectTile project={submitted} />);
    expect(screen.getByText("Permit Two-Tap")).toBeInTheDocument();
    expect(
      screen.getByText("Two taps from idle to signed permit."),
    ).toBeInTheDocument();
    expect(screen.getByText("Submitted")).toBeInTheDocument();
  });

  it("calls onTryIt with the project id", () => {
    const onTryIt = vi.fn();
    render(<ProjectTile project={submitted} onTryIt={onTryIt} />);
    fireEvent.click(screen.getByRole("button", { name: /try permit two-tap/i }));
    expect(onTryIt).toHaveBeenCalledWith("proj_1");
  });

  it("hides the Try it button while drafting", () => {
    const drafting: Project = { ...submitted, status: "drafting" };
    render(<ProjectTile project={drafting} />);
    expect(screen.queryByRole("button", { name: /try/i })).toBeNull();
    expect(screen.getByText("No artefact yet")).toBeInTheDocument();
  });

  it("matches the default snapshot", () => {
    const { container } = render(<ProjectTile project={submitted} />);
    expect(container.firstChild).toMatchSnapshot();
  });
});
