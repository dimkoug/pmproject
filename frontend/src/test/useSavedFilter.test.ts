import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useSavedFilter } from "../shell/useSavedFilter";

describe("useSavedFilter", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("initializes with defaults when no saved state", () => {
    const { result } = renderHook(() => useSavedFilter("page-a", { q: "", status: "all" }));
    const [filters] = result.current;
    expect(filters).toEqual({ q: "", status: "all" });
  });

  it("persists updates to localStorage", () => {
    const { result } = renderHook(() => useSavedFilter("page-b", { q: "", status: "all" }));
    act(() => {
      result.current[1]({ q: "acme" });
    });
    expect(result.current[0]).toEqual({ q: "acme", status: "all" });
    expect(JSON.parse(localStorage.getItem("filter:page-b")!)).toEqual({ q: "acme", status: "all" });
  });

  it("hydrates from localStorage on mount", () => {
    localStorage.setItem("filter:hydrate", JSON.stringify({ q: "remembered", status: "open" }));
    const { result } = renderHook(() => useSavedFilter("hydrate", { q: "", status: "all" }));
    expect(result.current[0]).toEqual({ q: "remembered", status: "open" });
  });

  it("merges partial updates", () => {
    const { result } = renderHook(() => useSavedFilter("merge", { a: 1, b: 2, c: 3 }));
    act(() => {
      result.current[1]({ b: 99 });
    });
    expect(result.current[0]).toEqual({ a: 1, b: 99, c: 3 });
  });

  it("reset clears both state and localStorage", () => {
    const { result } = renderHook(() => useSavedFilter("reset-key", { q: "" }));
    act(() => {
      result.current[1]({ q: "hello" });
    });
    expect(localStorage.getItem("filter:reset-key")).not.toBeNull();
    act(() => {
      result.current[2]();
    });
    expect(result.current[0]).toEqual({ q: "" });
    expect(localStorage.getItem("filter:reset-key")).toBeNull();
  });

  it("survives corrupt JSON in localStorage", () => {
    localStorage.setItem("filter:corrupt", "{not json}");
    const { result } = renderHook(() => useSavedFilter("corrupt", { q: "safe-default" }));
    expect(result.current[0]).toEqual({ q: "safe-default" });
  });

  it("missing keys in stored object fall back to defaults", () => {
    localStorage.setItem("filter:partial", JSON.stringify({ q: "hi" }));
    const { result } = renderHook(() => useSavedFilter("partial", { q: "", sort: "asc" }));
    expect(result.current[0]).toEqual({ q: "hi", sort: "asc" });
  });
});
