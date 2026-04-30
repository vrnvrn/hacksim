import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, render, screen } from "@testing-library/react";
import { SimErrorBanner } from "./SimErrorBanner";

class FakeEventSource {
  static instances: FakeEventSource[] = [];
  url: string;
  onopen: ((ev: Event) => void) | null = null;
  onerror: ((ev: Event) => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  listeners = new Map<string, ((ev: MessageEvent) => void)[]>();

  constructor(url: string) {
    this.url = url;
    FakeEventSource.instances.push(this);
  }

  addEventListener(name: string, fn: (ev: MessageEvent) => void) {
    const arr = this.listeners.get(name) ?? [];
    arr.push(fn);
    this.listeners.set(name, arr);
  }

  emitTyped(type: string, payload: unknown) {
    const ev = new MessageEvent(type, { data: JSON.stringify(payload) });
    const handlers = this.listeners.get(type) ?? [];
    for (const h of handlers) h(ev);
  }

  close() {}
}

describe("SimErrorBanner", () => {
  beforeEach(() => {
    FakeEventSource.instances = [];
    // @ts-expect-error attach mock
    globalThis.EventSource = FakeEventSource;
    vi.stubEnv("NEXT_PUBLIC_USE_MOCKS", "true");
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllEnvs();
  });

  it("renders nothing on idle stream", () => {
    const { container } = render(<SimErrorBanner simId="sim_x" />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders the orchestrator error message when sim.start_error fires", async () => {
    render(<SimErrorBanner simId="sim_x" />);
    const es = FakeEventSource.instances[0]!;
    await act(async () => {
      es.emitTyped("sim.start_error", { error: "AXL binary not executable" });
    });
    const alert = screen.getByRole("alert", { name: /simulation start error/i });
    expect(alert).toBeInTheDocument();
    expect(alert).toHaveTextContent(/AXL binary not executable/);
    expect(alert).toHaveTextContent(/make build-axl/);
    const startOver = screen.getByRole("link", { name: /start over/i });
    expect(startOver).toHaveAttribute("href", "/");
  });

  it("falls back to a generic message when the event has no error string", async () => {
    render(<SimErrorBanner simId="sim_x" />);
    const es = FakeEventSource.instances[0]!;
    await act(async () => {
      es.emitTyped("sim.start_error", {});
    });
    const alert = screen.getByRole("alert", { name: /simulation start error/i });
    expect(alert).toHaveTextContent(/orchestrator failed to spawn/i);
  });
});
