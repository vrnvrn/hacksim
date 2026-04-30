/**
 * HostedModeBanner reads the two relevant env vars at module load time, so
 * we exercise it via vi.resetModules + dynamic import so each test sees
 * fresh module-level state for the env vars.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

const HOSTED_KEY = "NEXT_PUBLIC_HOSTED_PREVIEW";
const MOCKS_KEY = "NEXT_PUBLIC_USE_MOCKS";

const originalHosted = process.env[HOSTED_KEY];
const originalMocks = process.env[MOCKS_KEY];

async function loadBanner() {
  vi.resetModules();
  const mod = await import("./HostedModeBanner");
  return mod.HostedModeBanner;
}

describe("HostedModeBanner", () => {
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

  it("renders nothing when neither env var is set (local dev)", async () => {
    const Banner = await loadBanner();
    const { container } = render(<Banner />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing when only mocks is on (local pnpm build)", async () => {
    process.env[MOCKS_KEY] = "true";
    const Banner = await loadBanner();
    const { container } = render(<Banner />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing when only hosted is on (Mode V2 with live orchestrator)", async () => {
    process.env[HOSTED_KEY] = "true";
    const Banner = await loadBanner();
    const { container } = render(<Banner />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders the fixture-mode notice when both env vars are true (Vercel V1)", async () => {
    process.env[HOSTED_KEY] = "true";
    process.env[MOCKS_KEY] = "true";
    const Banner = await loadBanner();
    render(<Banner />);

    const note = screen.getByRole("note", { name: /hosted preview notice/i });
    expect(note).toBeInTheDocument();
    expect(note).toHaveTextContent(/fixtures, not a live AXL mesh/i);
    expect(note).toHaveTextContent(/make demo/i);

    const repoLink = screen.getByRole("link", { name: /repo/i });
    expect(repoLink).toHaveAttribute("href", "https://github.com/vrnvrn/hacksim");
    expect(repoLink).toHaveAttribute("target", "_blank");
  });
});
