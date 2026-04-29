import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Footer } from "./Footer";

describe("Footer", () => {
  it("renders three columns with their headings", () => {
    render(<Footer />);
    expect(screen.getByText("HackSim")).toBeInTheDocument();
    expect(screen.getByText("Built on")).toBeInTheDocument();
    expect(screen.getByText("Code")).toBeInTheDocument();
  });

  it("links to the AXL repo", () => {
    render(<Footer />);
    const githubLink = screen.getByRole("link", { name: "GitHub" });
    expect(githubLink).toHaveAttribute("href", "https://github.com/gensyn-ai/axl");
  });

  it("matches the default snapshot", () => {
    const { container } = render(<Footer />);
    expect(container.firstChild).toMatchSnapshot();
  });
});
