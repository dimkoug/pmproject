import { useCallback, useState } from "react";

/**
 * Persist a filter object under a localStorage key. Survives reloads and
 * tab switches so users don't re-apply the same filters every time they
 * revisit a page.
 *
 * Usage:
 *   const [filters, setFilters, resetFilters] = useSavedFilter("trash", { entity: "" });
 *   <select value={filters.entity} onChange={e => setFilters({ entity: e.target.value })} />
 */
export function useSavedFilter<T extends Record<string, any>>(
  storageKey: string,
  defaults: T,
): readonly [T, (patch: Partial<T>) => void, () => void] {
  const fullKey = `filter:${storageKey}`;
  const [state, setState] = useState<T>(() => {
    if (typeof window === "undefined") return defaults;
    try {
      const raw = window.localStorage.getItem(fullKey);
      if (!raw) return defaults;
      return { ...defaults, ...(JSON.parse(raw) as Partial<T>) };
    } catch {
      return defaults;
    }
  });

  const update = useCallback((patch: Partial<T>) => {
    setState((prev) => {
      const next = { ...prev, ...patch } as T;
      try { window.localStorage.setItem(fullKey, JSON.stringify(next)); } catch { /* ignore quota */ }
      return next;
    });
  }, [fullKey]);

  const reset = useCallback(() => {
    setState(defaults);
    try { window.localStorage.removeItem(fullKey); } catch { /* ignore */ }
  }, [fullKey, defaults]);

  return [state, update, reset] as const;
}
