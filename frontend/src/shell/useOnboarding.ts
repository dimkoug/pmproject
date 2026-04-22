import { useCallback, useEffect, useState } from "react";
import { useAppSelector } from "../app/hooks";
import { notifyUser } from "./modalService";

const API = (import.meta.env.VITE_API_URL as string) || "";

export type OnboardingStep = { key: string; title: string; description: string };
export type OnboardingStatus = {
  steps: OnboardingStep[];
  completed: string[];
  remaining: string[];
  skipped: boolean;
  finished: boolean;
  show_wizard: boolean;
};

/**
 * Wraps /api/onboarding/* so the wizard can poll state + post completions
 * without owning its own Redux slice. Re-fetches once on login. Mutation
 * errors surface through `notifyUser` rather than silently leaving the UI
 * out of sync with the server.
 */
export function useOnboarding() {
  const token = useAppSelector((s) => s.auth.token);
  const [status, setStatus] = useState<OnboardingStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const authHeader = token ? { Authorization: `Bearer ${token}` } : undefined;

  const refresh = useCallback(async () => {
    if (!token) { setStatus(null); return; }
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/onboarding/status`, { headers: authHeader });
      if (!r.ok) { setStatus(null); return; }
      setStatus((await r.json()) as OnboardingStatus);
    } catch {
      setStatus(null);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { void refresh(); }, [refresh]);

  const completeStep = useCallback(async (key: string) => {
    if (!token) return;
    setError(null);
    try {
      const r = await fetch(`${API}/api/onboarding/steps/${encodeURIComponent(key)}`, {
        method: "POST",
        headers: authHeader,
      });
      if (!r.ok) {
        const msg = `Step update failed (HTTP ${r.status})`;
        setError(msg);
        await notifyUser({ title: "Could not save progress", description: msg });
        return;
      }
      setStatus((await r.json()) as OnboardingStatus);
    } catch (e: any) {
      const msg = e?.message || "Network error";
      setError(msg);
      await notifyUser({ title: "Could not save progress", description: msg });
    }
  }, [token]);

  const skip = useCallback(async () => {
    if (!token) return;
    setError(null);
    try {
      const r = await fetch(`${API}/api/onboarding/skip`, { method: "POST", headers: authHeader });
      if (!r.ok) {
        const msg = `Skip failed (HTTP ${r.status})`;
        setError(msg);
        await notifyUser({ title: "Could not dismiss wizard", description: msg });
        return;
      }
      setStatus((prev) => (prev ? { ...prev, skipped: true, show_wizard: false } : prev));
    } catch (e: any) {
      const msg = e?.message || "Network error";
      setError(msg);
      await notifyUser({ title: "Could not dismiss wizard", description: msg });
    }
  }, [token]);

  return { status, loading, error, refresh, completeStep, skip };
}
