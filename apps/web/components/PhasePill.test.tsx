import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { PhasePill } from "./PhasePill";

describe("PhasePill", () => {
  it("shows the phase label and a screen-reader partner", () => {
    render(<PhasePill phase={2} />);
    expect(screen.getByText("Phase: building")).toBeInTheDocument();
    expect(screen.getByText("Current phase: building")).toBeInTheDocument();
  });

  it("matches the default snapshot for phase 2", () => {
    const { container } = render(<PhasePill phase={2} />);
    expect(container.firstChild).toMatchSnapshot();
  });
});
