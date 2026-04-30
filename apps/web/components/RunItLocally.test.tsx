import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { RunItLocally } from "./RunItLocally";

describe("RunItLocally", () => {
  it("renders the run-it-locally anchor id so the banner deep link resolves", () => {
    const { container } = render(<RunItLocally />);
    const section = container.querySelector("#run-it-locally");
    expect(section).not.toBeNull();
    expect(section?.tagName.toLowerCase()).toBe("section");
  });

  it("shows the canonical quickstart in a code block", () => {
    render(<RunItLocally />);
    const heading = screen.getByRole("heading", { name: /quickstart/i });
    expect(heading).toBeInTheDocument();
    // git clone, make build-axl, and make hooks-install appear only inside
    // the quickstart block. make demo also appears in the verify block, so
    // we assert it shows up at least once via getAllByText.
    for (const cmd of [
      "git clone https://github.com/vrnvrn/hacksim",
      "make build-axl",
      "make hooks-install",
    ]) {
      expect(screen.getByText(new RegExp(cmd))).toBeInTheDocument();
    }
    expect(screen.getAllByText(/make demo/).length).toBeGreaterThan(0);
  });

  it("includes the integration test in the verification block", () => {
    render(<RunItLocally />);
    expect(
      screen.getByText(/pytest tests\/integration\/test_two_node_send\.py -q/),
    ).toBeInTheDocument();
    expect(screen.getByText(/tcpdump -i lo0/)).toBeInTheDocument();
    expect(screen.getByText(/third_party\/axl\/node/)).toBeInTheDocument();
  });

  it("links docs/process and docs/ARCHITECTURE.md by absolute URL", () => {
    render(<RunItLocally />);
    const processLink = screen.getByRole("link", { name: /docs\/process/i });
    expect(processLink).toHaveAttribute(
      "href",
      "https://github.com/vrnvrn/hacksim/tree/main/docs/process",
    );
    const archLink = screen.getByRole("link", { name: /docs\/ARCHITECTURE/i });
    expect(archLink).toHaveAttribute(
      "href",
      "https://github.com/vrnvrn/hacksim/blob/main/docs/ARCHITECTURE.md",
    );
  });
});
