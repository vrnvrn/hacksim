import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { RunLog } from "./RunLog";

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

  emit(data: unknown) {
    const ev = new MessageEvent("message", { data: JSON.stringify(data) });
    this.onmessage?.(ev);
  }

  emitTyped(type: string, payload: unknown) {
    const ev = new MessageEvent(type, { data: JSON.stringify(payload) });
    const handlers = this.listeners.get(type) ?? [];
    for (const h of handlers) h(ev);
  }

  close() {}
}

describe("RunLog", () => {
  beforeEach(() => {
    FakeEventSource.instances = [];
    // @ts-expect-error attach mock
    globalThis.EventSource = FakeEventSource;
    vi.stubEnv("NEXT_PUBLIC_USE_MOCKS", "true");
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("renders an empty state then appends an envelope", async () => {
    render(<RunLog simId="sim_x" />);
    expect(
      screen.getByText(/booting the agents/i),
    ).toBeInTheDocument();
    const es = FakeEventSource.instances[0]!;
    await act(async () => {
      es.emitTyped("bounty.posted", {
        id: "bnt_1",
        title: "Best UX",
        sponsor_name: "FoldLab",
        sender_id: "f".repeat(64),
      });
    });
    expect(screen.getByText("bounty.posted")).toBeInTheDocument();
    expect(screen.getByText(/Best UX/)).toBeInTheDocument();
  });

  it("offers a pause toggle", () => {
    render(<RunLog simId="sim_x" />);
    expect(
      screen.getByRole("button", { name: /pause run log/i }),
    ).toBeInTheDocument();
  });
});
