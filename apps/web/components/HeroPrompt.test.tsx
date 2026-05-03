import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HeroPrompt } from "./HeroPrompt";

describe("HeroPrompt", () => {
  it("renders the textarea with the placeholder", () => {
    render(<HeroPrompt onSubmit={() => {}} />);
    expect(
      screen.getByPlaceholderText(
        "an onchain agents hackathon with five sponsors and a $5k pool",
      ),
    ).toBeInTheDocument();
  });

  it("submits with default config when clicking Spin up sim", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<HeroPrompt onSubmit={onSubmit} />);
    const textarea = screen.getByLabelText("Describe the hackathon you want");
    await user.type(textarea, "a tiny test hackathon");
    await user.click(screen.getByRole("button", { name: "Spin up sim" }));
    expect(onSubmit).toHaveBeenCalledWith(
      "a tiny test hackathon",
      expect.objectContaining({ builders: 5, judges: 3, designers: 2 }),
    );
  });

  it("blocks submit on empty prompt and shows an inline error", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<HeroPrompt onSubmit={onSubmit} />);
    await user.click(screen.getByRole("button", { name: "Spin up sim" }));
    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(/add a prompt/i);
  });

  it("submits on Enter, allows newline on Shift+Enter", () => {
    const onSubmit = vi.fn();
    render(<HeroPrompt onSubmit={onSubmit} />);
    const textarea = screen.getByLabelText(
      "Describe the hackathon you want",
    ) as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: "hello" } });
    fireEvent.keyDown(textarea, { key: "Enter", shiftKey: false });
    expect(onSubmit).toHaveBeenCalledTimes(1);
  });

  it("matches the default snapshot", () => {
    const { container } = render(<HeroPrompt onSubmit={() => {}} />);
    expect(container.firstChild).toMatchSnapshot();
  });

  describe("self-managed POST (no onSubmit)", () => {
    afterEach(() => {
      vi.unstubAllGlobals();
    });

    function fillAndSubmit() {
      const textarea = screen.getByLabelText(
        "Describe the hackathon you want",
      ) as HTMLTextAreaElement;
      fireEvent.change(textarea, { target: { value: "a tiny test sim" } });
      fireEvent.click(screen.getByRole("button", { name: "Spin up sim" }));
    }

    it("surfaces a non-2xx status with body excerpt", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn().mockResolvedValue({
          ok: false,
          status: 500,
          text: async () => "spawner failure: bind 127.0.0.1:9100",
        }),
      );
      render(<HeroPrompt />);
      fillAndSubmit();
      await waitFor(() => {
        const alert = screen.getByRole("alert");
        expect(alert).toHaveTextContent(/returned 500/);
        expect(alert).toHaveTextContent(/spawner failure: bind/);
      });
    });

    it("surfaces an abort as the 12-second timeout message", async () => {
      vi.stubGlobal(
        "fetch",
        vi
          .fn()
          .mockRejectedValue(new DOMException("aborted", "AbortError")),
      );
      render(<HeroPrompt />);
      fillAndSubmit();
      await waitFor(() => {
        expect(screen.getByRole("alert")).toHaveTextContent(
          /longer than 12 seconds/,
        );
      });
    });

    it("surfaces a network failure as the make demo hint", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn().mockRejectedValue(new TypeError("Failed to fetch")),
      );
      render(<HeroPrompt />);
      fillAndSubmit();
      await waitFor(() => {
        expect(screen.getByRole("alert")).toHaveTextContent(
          /could not reach the orchestrator/i,
        );
      });
    });
  });
});
