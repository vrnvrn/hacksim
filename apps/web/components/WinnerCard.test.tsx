import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { WinnerCard } from "./WinnerCard";
import type { Bounty, Project } from "@/lib/types";

const project: Project = {
  id: "proj_1",
  team_id: "team_1",
  bounty_id: "bnty_1",
  title: "Permit Two-Tap",
  tagline: "Two taps from idle to signed permit.",
  description: "",
  status: "judged",
  submitted_at: null,
  commit_hash: null,
  entry_path: "index.html",
  artefact_path: "/x",
  github_url: null,
};

const prize: Bounty = {
  id: "bnty_1",
  title: "Best onchain UX",
  sponsor_name: "Permit Labs",
  sponsor_peer_id: "0".repeat(64),
  prize_amount_usd: 1500,
  description: "",
  qualification: [],
  created_at: "2026-04-28T00:00:00Z",
};

describe("WinnerCard", () => {
  it("renders the rank ribbon for first place", () => {
    render(
      <WinnerCard
        project={project}
        rank={1}
        prize={prize}
        onTryIt={() => {}}
      />,
    );
    expect(screen.getByText("1st")).toBeInTheDocument();
  });

  it("calls onTryIt when the button is clicked", () => {
    const onTryIt = vi.fn();
    render(
      <WinnerCard
        project={project}
        rank={2}
        prize={prize}
        onTryIt={onTryIt}
      />,
    );
    fireEvent.click(screen.getByRole("button"));
    expect(onTryIt).toHaveBeenCalled();
  });

  it("matches the default snapshot", () => {
    const { container } = render(
      <WinnerCard
        project={project}
        rank={1}
        prize={prize}
        onTryIt={() => {}}
      />,
    );
    expect(container.firstChild).toMatchSnapshot();
  });
});
