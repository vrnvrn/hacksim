import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import AgentSetupPage from "./page";

describe("AgentSetupPage", () => {
  beforeEach(() => {
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText: vi.fn().mockResolvedValue(undefined) },
    });
  });

  it("renders the headline aimed at the human reader", () => {
    render(<AgentSetupPage />);
    expect(
      screen.getByRole("heading", {
        level: 1,
        name: /hand this to your coding agent/i,
      }),
    ).toBeInTheDocument();
  });

  it("embeds the AgentInstructions copy block", () => {
    render(<AgentSetupPage />);
    expect(
      screen.getByRole("button", {
        name: /copy setup instructions to clipboard/i,
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/git clone https:\/\/github\.com\/vrnvrn\/hacksim/),
    ).toBeInTheDocument();
  });

  it("links back to the full quickstart on /docs", () => {
    render(<AgentSetupPage />);
    const link = screen.getByRole("link", {
      name: /full quickstart on \/docs/i,
    });
    expect(link).toHaveAttribute("href", "/docs#run-it-locally");
  });

  it("renders nav and footer landmarks", () => {
    render(<AgentSetupPage />);
    expect(screen.getByRole("banner")).toBeInTheDocument();
    expect(screen.getByRole("contentinfo")).toBeInTheDocument();
  });
});
