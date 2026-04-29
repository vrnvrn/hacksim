import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatPill } from "./StatPill";

describe("StatPill", () => {
  it("renders the label", () => {
    render(<StatPill label="12 agents" />);
    expect(screen.getByText("12 agents")).toBeInTheDocument();
  });

  it("applies tone class", () => {
    render(<StatPill label="ok" tone="success" />);
    const el = screen.getByText("ok");
    expect(el.className).toContain("bg-success-soft");
  });

  it("matches the default snapshot", () => {
    const { container } = render(<StatPill label="3 bounties" />);
    expect(container.firstChild).toMatchSnapshot();
  });
});
