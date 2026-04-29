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

  emitTyped(type: string, payload: unknown) {
    const ev = new MessageEvent(type, { data: JSON.stringify(payload) });
    const handlers = this.listeners[type] ?? [];
    for (const h of handlers) h(ev);
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

  it("forwards typed SSE events as Envelopes", () => {
    const onEvent = vi.fn();
    renderHook(() => useSse("sim_x", onEvent));
    const es = FakeEventSource.instances[0]!;
    act(() => {
      es.emitTyped("phase.tick", { phase: 1, id: "phase_1" });
    });
    expect(onEvent).toHaveBeenCalledTimes(1);
    const arg = onEvent.mock.calls[0]![0];
    expect(arg.type).toBe("phase.tick");
    expect(arg.data).toEqual({ phase: 1, id: "phase_1" });
    expect(typeof arg.ts).toBe("string");
  });

  it("falls back to default message events when no event type is set", () => {
    const onEvent = vi.fn();
    renderHook(() => useSse("sim_x", onEvent));
    const es = FakeEventSource.instances[0]!;
    act(() => {
      es.emit({ type: "sim.created", sim_id: "sim_x" });
    });
    expect(onEvent).toHaveBeenCalledTimes(1);
    const arg = onEvent.mock.calls[0]![0];
    expect(arg.type).toBe("sim.created");
    expect(arg.data).toEqual({ type: "sim.created", sim_id: "sim_x" });
  });

  it("closes the EventSource on unmount", () => {
    const { unmount } = renderHook(() => useSse("sim_x", () => {}));
    const es = FakeEventSource.instances[0]!;
    unmount();
    expect(es.closed).toBe(true);
  });
});
