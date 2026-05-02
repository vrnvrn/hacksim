import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { AgentInstructions } from "./AgentInstructions";

describe("AgentInstructions", () => {
  let writeText: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });
  });

  it("renders the instruction block with the canonical clone url", () => {
    render(<AgentInstructions />);
    expect(
      screen.getByText(/git clone https:\/\/github\.com\/vrnvrn\/hacksim/),
    ).toBeInTheDocument();
    expect(screen.getByText(/make build-axl/)).toBeInTheDocument();
    expect(screen.getByText(/make demo/)).toBeInTheDocument();
    expect(screen.getByText(/ANTHROPIC_API_KEY/)).toBeInTheDocument();
  });

  it("exposes the block as a labelled region for screen readers", () => {
    render(<AgentInstructions />);
    expect(
      screen.getByLabelText(
        /HackSim setup instructions, copy to share with a coding agent/i,
      ),
    ).toBeInTheDocument();
  });

  it("copies the instructions to the clipboard and flips the button label", async () => {
    render(<AgentInstructions />);
    const button = screen.getByRole("button", {
      name: /copy setup instructions to clipboard/i,
    });
    expect(button).toHaveTextContent(/copy/i);
    fireEvent.click(button);
    await waitFor(() => expect(writeText).toHaveBeenCalledOnce());
    const written = writeText.mock.calls[0][0] as string;
    expect(written).toContain("git clone https://github.com/vrnvrn/hacksim");
    expect(written).toContain("make demo");
    await waitFor(() => expect(button).toHaveTextContent(/copied/i));
  });
});
