import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { EmptyState } from "./EmptyState";

describe("EmptyState", () => {
  it("renders title and body", () => {
    render(<EmptyState title="No data" body="Try a different prompt." />);
    expect(screen.getByText("No data")).toBeInTheDocument();
    expect(screen.getByText("Try a different prompt.")).toBeInTheDocument();
  });

  it("renders an optional CTA", () => {
    render(
      <EmptyState
        title="Nothing here"
        body="Try again."
        cta={<button>Retry</button>}
      />,
    );
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("matches the default snapshot", () => {
    const { container } = render(
      <EmptyState title="No data" body="Try again." />,
    );
    expect(container.firstChild).toMatchSnapshot();
  });
});
