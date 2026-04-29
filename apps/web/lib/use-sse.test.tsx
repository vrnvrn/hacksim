import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useSse } from "./use-sse";

class FakeEventSource {
  static instances: FakeEventSource[] = [];
  url: string;
  onopen: ((ev: Event) => void) | null = null;
  onerror: ((ev: Event) => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  closed = false;
  listeners: Record<string, Array<(ev: MessageEvent) => void>> = {};

  constructor(url: string) {
    this.url = url;
    FakeEventSource.instances.push(this);
  }

  addEventListener(name: string, fn: (ev: MessageEvent) => void) {
    this.listeners[name] ??= [];
    this.listeners[name]!.push(fn);
  }

  emit(data: unknown) {
    const ev = new MessageEvent("message", { data: JSON.stringify(data) });
    this.onmessage?.(ev);
  }

  close() {
    this.closed = true;
  }
}

describe("useSse", () => {
  beforeEach(() => {
    FakeEventSource.instances = [];
    // @ts-expect-error attach mock
    globalThis.EventSource = FakeEventSource;
    vi.stubEnv("NEXT_PUBLIC_USE_MOCKS", "true");
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("opens an EventSource at the mock stream url", () => {
    renderHook(() => useSse("sim_x", () => {}));
    expect(FakeEventSource.instances).toHaveLength(1);
    expect(FakeEventSource.instances[0]!.url).toContain("/api/mocks/stream");
  });

  it("forwards parsed envelopes to onEvent", () => {
    const onEvent = vi.fn();
    renderHook(() => useSse("sim_x", onEvent));
    const es = FakeEventSource.instances[0]!;
    act(() => {
      es.emit({ type: "phase.tick", data: { phase: 1 } });
    });
    expect(onEvent).toHaveBeenCalledWith({
      type: "phase.tick",
      data: { phase: 1 },
    });
  });

  it("closes the EventSource on unmount", () => {
    const { unmount } = renderHook(() => useSse("sim_x", () => {}));
    const es = FakeEventSource.instances[0]!;
    unmount();
    expect(es.closed).toBe(true);
  });
});
