import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Footer } from "./Footer";

describe("Footer", () => {
  it("renders three columns with their headings", () => {
    render(<Footer />);
    expect(screen.getAllByText("HackSim").length).toBeGreaterThan(0);
    expect(screen.getByText("Built on")).toBeInTheDocument();
  });

  it("links to the HackSim github repo", () => {
    render(<Footer />);
    const githubLink = screen.getByRole("link", {
      name: /github.com\/vrnvrn\/hacksim/i,
    });
    expect(githubLink).toHaveAttribute(
      "href",
      "https://github.com/vrnvrn/hacksim",
    );
  });

  it("credits ETHGlobal Open Agents 2026", () => {
    render(<Footer />);
    expect(
      screen.getByRole("link", { name: /ethglobal open agents 2026/i }),
    ).toBeInTheDocument();
  });

  it("matches the default snapshot", () => {
    const { container } = render(<Footer />);
    expect(container.firstChild).toMatchSnapshot();
  });
});
