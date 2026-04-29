import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { BuilderChip } from "./BuilderChip";
import type { Builder } from "@/lib/types";

const sample: Builder = {
  peer_id: "f".repeat(64),
  display_name: "Aiko Tanaka",
  skills: ["typescript", "three.js", "shaders"],
  team_id: "team_alpha",
  current_bounty_id: "bnty_1",
  persona_excerpt:
    "Loves writing tiny scenes that run at 60fps on a phone.",
};

describe("BuilderChip", () => {
  it("renders the display name and first two skills", () => {
    render(<BuilderChip builder={sample} />);
    expect(screen.getByText("Aiko Tanaka")).toBeInTheDocument();
    expect(screen.getByText(/typescript, three.js/)).toBeInTheDocument();
  });

  it("calls onSelect when clicked", () => {
    const onSelect = vi.fn();
    render(<BuilderChip builder={sample} onSelect={onSelect} />);
    fireEvent.click(screen.getByRole("button"));
    expect(onSelect).toHaveBeenCalled();
  });

  it("matches the default snapshot", () => {
    const { container } = render(<BuilderChip builder={sample} />);
    expect(container.firstChild).toMatchSnapshot();
  });
});
