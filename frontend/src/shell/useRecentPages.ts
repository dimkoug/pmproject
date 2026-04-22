import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";

export type RecentPage = { to: string; label: string; at: number };

const KEY = "recentPages";
const MAX = 5;
// Routes we don't want showing up under "Recent" — top-level hubs, mount points.
const IGNORE = new Set<string>(["/", "/login", "/forgot-password", "/reset-password", "/logout"]);

function readAll(): RecentPage[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as RecentPage[]) : [];
  } catch {
    return [];
  }
}

function writeAll(items: RecentPage[]) {
  try { window.localStorage.setItem(KEY, JSON.stringify(items.slice(0, MAX))); } catch { /* ignore */ }
}

function labelFor(pathname: string): string {
  // Heuristic: last segment, humanised. Replace UUIDs with "Details" so we
  // don't leak random ids into the label.
  const parts = pathname.split("/").filter(Boolean);
  const uuidish = /^[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}$/i;
  const last = parts[parts.length - 1] ?? "Home";
  if (uuidish.test(last)) return parts.length >= 2 ? `${humanise(parts[parts.length - 2])} detail` : "Detail";
  return humanise(last);
}

function humanise(seg: string): string {
  return seg.replace(/[-_]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Subscribe to route changes and track the N most-recent pages in localStorage. */
export function useRecentPages(): RecentPage[] {
  const { pathname } = useLocation();
  const [items, setItems] = useState<RecentPage[]>(() => readAll());

  useEffect(() => {
    if (IGNORE.has(pathname)) return;
    const next: RecentPage = { to: pathname, label: labelFor(pathname), at: Date.now() };
    setItems((prev) => {
      const deduped = prev.filter((p) => p.to !== pathname);
      const merged = [next, ...deduped].slice(0, MAX);
      writeAll(merged);
      return merged;
    });
  }, [pathname]);

  return items;
}
