import { describe, it, expect, beforeEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import type { ReactNode } from "react";
import { useRecentPages } from "../shell/useRecentPages";

function wrap(initialPath: string) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <MemoryRouter initialEntries={[initialPath]}>{children}</MemoryRouter>;
  };
}

describe("useRecentPages", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("records the current path on mount", () => {
    const { result } = renderHook(() => useRecentPages(), {
      wrapper: wrap("/projects/abc"),
    });
    expect(result.current[0].to).toBe("/projects/abc");
  });

  it("humanises the label from the URL segment", () => {
    const { result } = renderHook(() => useRecentPages(), {
      wrapper: wrap("/finance/purchase-orders"),
    });
    expect(result.current[0].label).toBe("Purchase Orders");
  });

  it("labels UUID segments as '{parent} detail'", () => {
    const { result } = renderHook(() => useRecentPages(), {
      wrapper: wrap("/projects/550e8400-e29b-41d4-a716-446655440000"),
    });
    expect(result.current[0].label).toContain("detail");
  });

  it("does not track ignored paths like /login", () => {
    const { result } = renderHook(() => useRecentPages(), {
      wrapper: wrap("/login"),
    });
    expect(result.current).toEqual([]);
  });

  it("persists to localStorage under 'recentPages'", () => {
    renderHook(() => useRecentPages(), { wrapper: wrap("/dashboard") });
    const stored = JSON.parse(localStorage.getItem("recentPages") || "[]");
    expect(stored).toHaveLength(1);
    expect(stored[0].to).toBe("/dashboard");
  });

  it("reads prior entries on mount", () => {
    localStorage.setItem("recentPages", JSON.stringify([
      { to: "/prior", label: "Prior", at: Date.now() - 10000 },
    ]));
    const { result } = renderHook(() => useRecentPages(), {
      wrapper: wrap("/current"),
    });
    // Current first, prior second
    expect(result.current[0].to).toBe("/current");
    expect(result.current.some((r) => r.to === "/prior")).toBe(true);
  });
});
