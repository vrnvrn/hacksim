import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

const HOSTED_KEY = "NEXT_PUBLIC_HOSTED_PREVIEW";
const MOCKS_KEY = "NEXT_PUBLIC_USE_MOCKS";

const originalHosted = process.env[HOSTED_KEY];
const originalMocks = process.env[MOCKS_KEY];

async function loadPill() {
  vi.resetModules();
  const mod = await import("./RecordedRunPill");
  return mod.RecordedRunPill;
}

describe("RecordedRunPill", () => {
  beforeEach(() => {
    delete process.env[HOSTED_KEY];
    delete process.env[MOCKS_KEY];
  });

  afterEach(() => {
    cleanup();
    if (originalHosted === undefined) delete process.env[HOSTED_KEY];
    else process.env[HOSTED_KEY] = originalHosted;
    if (originalMocks === undefined) delete process.env[MOCKS_KEY];
    else process.env[MOCKS_KEY] = originalMocks;
  });

  it("renders nothing on local dev (no env vars)", async () => {
    const Pill = await loadPill();
    const { container } = render(<Pill createdAt="2026-04-28T12:00:00Z" />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing on Mode V2 (hosted but mocks off)", async () => {
    process.env[HOSTED_KEY] = "true";
    const Pill = await loadPill();
    const { container } = render(<Pill createdAt="2026-04-28T12:00:00Z" />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders the recorded date when hosted preview is on", async () => {
    process.env[HOSTED_KEY] = "true";
    process.env[MOCKS_KEY] = "true";
    const Pill = await loadPill();
    render(<Pill createdAt="2026-04-28T12:00:00Z" />);

    const pill = screen.getByRole("status", {
      name: /recorded run from 2026-04-28/i,
    });
    expect(pill).toBeInTheDocument();
    expect(pill).toHaveTextContent(/2026-04-28/);
    expect(pill).toHaveTextContent(/recorded/i);
  });

  it("falls back to the raw string when the date is malformed", async () => {
    process.env[HOSTED_KEY] = "true";
    process.env[MOCKS_KEY] = "true";
    const Pill = await loadPill();
    render(<Pill createdAt="garbage" />);

    expect(screen.getByRole("status")).toHaveTextContent("garbage");
  });
});
