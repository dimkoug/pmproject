import { describe, it, expect } from "vitest";
import { createTestStore } from "./test-utils";

describe("Redux Store", () => {
  it("should create store with initial state", () => {
    const store = createTestStore();
    const state = store.getState();
    expect(state.ws).toBeDefined();
    expect(state.ws.connected).toBe(false);
    expect(state.ws.events).toEqual([]);
    expect(state.api).toBeDefined();
  });

  it("should have api reducer path", () => {
    const store = createTestStore();
    const state = store.getState();
    expect(state).toHaveProperty("api");
  });

  it("should dispatch ws actions", () => {
    const store = createTestStore();
    store.dispatch({ type: "ws/wsConnected" });
    expect(store.getState().ws.connected).toBe(true);
    store.dispatch({ type: "ws/wsDisconnected" });
    expect(store.getState().ws.connected).toBe(false);
  });
});
