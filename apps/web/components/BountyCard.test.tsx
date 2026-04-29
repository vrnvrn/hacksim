import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { BountyCard } from "./BountyCard";
import type { Bounty } from "@/lib/types";

const sample: Bounty = {
  id: "bnty_1",
  title: "Best onchain UX for permits",
  sponsor_name: "Permit Labs",
  sponsor_peer_id: "0".repeat(64),
  prize_amount_usd: 1500,
  description: "Build the smoothest two-tap permit flow. No browser extension hacks.",
  qualification: ["Works on a fresh wallet", "Mobile-friendly"],
  created_at: "2026-04-28T12:00:00Z",
};

describe("BountyCard", () => {
  it("renders title, sponsor and prize", () => {
    render(<BountyCard bounty={sample} />);
    expect(screen.getByText("Best onchain UX for permits")).toBeInTheDocument();
    expect(screen.getByText("Permit Labs")).toBeInTheDocument();
    expect(screen.getByText("$1,500")).toBeInTheDocument();
  });

  it("lists qualification items", () => {
    render(<BountyCard bounty={sample} />);
    expect(screen.getByText("Works on a fresh wallet")).toBeInTheDocument();
    expect(screen.getByText("Mobile-friendly")).toBeInTheDocument();
  });

  it("matches the default snapshot", () => {
    const { container } = render(<BountyCard bounty={sample} />);
    expect(container.firstChild).toMatchSnapshot();
  });
});
