import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { HowItWorks } from "./HowItWorks";

describe("HowItWorks", () => {
  it("renders the three cards", () => {
    render(<HowItWorks />);
    expect(screen.getByText("You prompt")).toBeInTheDocument();
    expect(screen.getByText("Agents organise")).toBeInTheDocument();
    expect(screen.getByText("You watch and play")).toBeInTheDocument();
  });

  it("uses a section labelled by the heading", () => {
    render(<HowItWorks />);
    expect(
      screen.getByRole("region", { name: "How it works" }),
    ).toBeInTheDocument();
  });

  it("matches the default snapshot", () => {
    const { container } = render(<HowItWorks />);
    expect(container.firstChild).toMatchSnapshot();
  });
});
