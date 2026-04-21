import { describe, it, expect } from "vitest";
import wsReducer, {
  wsConnected,
  wsDisconnected,
  wsEventReceived,
  wsClearEvents,
} from "../services/wsSlice";

describe("wsSlice", () => {
  const initialState = { connected: false, events: [] };

  it("should return initial state", () => {
    expect(wsReducer(undefined, { type: "unknown" })).toEqual(initialState);
  });

  it("should handle wsConnected", () => {
    const state = wsReducer(initialState, wsConnected());
    expect(state.connected).toBe(true);
  });

  it("should handle wsDisconnected", () => {
    const connected = { connected: true, events: [] };
    const state = wsReducer(connected, wsDisconnected());
    expect(state.connected).toBe(false);
  });

  it("should handle wsEventReceived", () => {
    const state = wsReducer(
      initialState,
      wsEventReceived({ event: "task_created", data: { id: "1", title: "Test" } })
    );
    expect(state.events).toHaveLength(1);
    expect(state.events[0].event).toBe("task_created");
    expect(state.events[0].data.title).toBe("Test");
    expect(state.events[0].timestamp).toBeGreaterThan(0);
  });

  it("should limit events to 50", () => {
    let state: any = initialState;
    for (let i = 0; i < 60; i++) {
      state = wsReducer(
        state,
        wsEventReceived({ event: `event_${i}`, data: { i } })
      );
    }
    expect(state.events).toHaveLength(50);
    expect(state.events[0].event).toBe("event_10");
    expect(state.events[49].event).toBe("event_59");
  });

  it("should handle wsClearEvents", () => {
    const withEvents = wsReducer(
      initialState,
      wsEventReceived({ event: "test", data: {} })
    );
    expect(withEvents.events).toHaveLength(1);

    const cleared = wsReducer(withEvents, wsClearEvents());
    expect(cleared.events).toHaveLength(0);
  });

  it("should keep connected state when receiving events", () => {
    const connected = { connected: true, events: [] };
    const state = wsReducer(
      connected,
      wsEventReceived({ event: "test", data: {} })
    );
    expect(state.connected).toBe(true);
  });
});
