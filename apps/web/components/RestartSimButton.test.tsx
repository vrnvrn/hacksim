import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { RestartSimButton } from "./RestartSimButton";

describe("RestartSimButton", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the label and icon", () => {
    vi.stubGlobal("confirm", vi.fn(() => false));
    render(<RestartSimButton />);
    expect(
      screen.getByRole("button", { name: "Restart simulation" }),
    ).toBeInTheDocument();
  });

  it("does nothing when the user cancels the confirm prompt", () => {
    vi.stubGlobal("confirm", vi.fn(() => false));
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    render(<RestartSimButton />);
    fireEvent.click(
      screen.getByRole("button", { name: "Restart simulation" }),
    );
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("calls POST /api/sim/reset on confirm", async () => {
    vi.stubGlobal("confirm", vi.fn(() => true));
    const fetchMock = vi
      .fn()
      .mockResolvedValue({ ok: true, status: 204 } as Response);
    vi.stubGlobal("fetch", fetchMock);
    // jsdom's window.location.href setter does navigate, but assigning a
    // bare path under the default origin sometimes throws. Override it
    // for the duration of this test.
    const originalLocation = window.location;
    Object.defineProperty(window, "location", {
      configurable: true,
      writable: true,
      value: { ...originalLocation, href: "" },
    });
    render(<RestartSimButton />);
    fireEvent.click(
      screen.getByRole("button", { name: "Restart simulation" }),
    );
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/sim/reset", {
        method: "POST",
      });
    });
    Object.defineProperty(window, "location", {
      configurable: true,
      writable: true,
      value: originalLocation,
    });
  });

  it("surfaces a non-2xx status as an inline error", async () => {
    vi.stubGlobal("confirm", vi.fn(() => true));
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 502 } as Response),
    );
    render(<RestartSimButton />);
    fireEvent.click(
      screen.getByRole("button", { name: "Restart simulation" }),
    );
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/reset returned 502/);
    });
  });
});
