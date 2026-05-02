import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Nav } from "./Nav";

describe("Nav", () => {
  it("renders the wordmark and four primary links", () => {
    render(<Nav />);
    expect(screen.getByLabelText("HackSim home")).toBeInTheDocument();
    const agentSetup = screen.getByRole("link", { name: /agent setup/i });
    expect(agentSetup).toBeInTheDocument();
    expect(agentSetup).toHaveAttribute("href", "/agent-setup");
    expect(screen.getByRole("link", { name: /examples/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /docs/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /github/i })).toBeInTheDocument();
  });

  it("has banner landmark and primary nav landmark", () => {
    const { container } = render(<Nav />);
    expect(container.querySelector("header[role='banner']")).not.toBeNull();
    expect(screen.getByRole("navigation", { name: "Primary" })).toBeInTheDocument();
  });

  it("matches the default snapshot", () => {
    const { container } = render(<Nav />);
    expect(container.firstChild).toMatchSnapshot();
  });
});
