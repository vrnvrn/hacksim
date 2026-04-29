import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { BuilderRoster } from "./BuilderRoster";
import type { Builder } from "@/lib/types";

const builders: Builder[] = [
  {
    peer_id: "a".repeat(64),
    display_name: "Aiko Tanaka",
    skills: ["typescript"],
    team_id: null,
    current_bounty_id: null,
  },
  {
    peer_id: "b".repeat(64),
    display_name: "Beni Carter",
    skills: ["d3"],
    team_id: null,
    current_bounty_id: null,
  },
];

describe("BuilderRoster", () => {
  it("renders one chip per builder", () => {
    render(<BuilderRoster builders={builders} />);
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
  });

  it("shows an empty message when builders is empty", () => {
    render(<BuilderRoster builders={[]} />);
    expect(screen.getByText(/no builders connected/i)).toBeInTheDocument();
  });

  it("matches the default snapshot", () => {
    const { container } = render(<BuilderRoster builders={builders} />);
    expect(container.firstChild).toMatchSnapshot();
  });
});
