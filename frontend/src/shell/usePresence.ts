import { useEffect, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

type Viewer = { user_id: string; name: string; email: string; last_seen: number };

/** Heartbeat presence on an entity + return the live list of other viewers.
 *  Heartbeats every 20s. Leave is sent on unmount. Backend TTL is 45s. */
export function usePresence(entityType: string | null, entityId: string | null): Viewer[] {
  const [viewers, setViewers] = useState<Viewer[]>([]);

  useEffect(() => {
    if (!entityType || !entityId) return;
    const token = localStorage.getItem("token");
    if (!token) return;
    const headers = { Authorization: `Bearer ${token}` };
    let cancelled = false;

    const beat = async () => {
      try {
        await fetch(`${API_URL}/api/presence/${entityType}/${entityId}`, { method: "POST", headers });
        const r = await fetch(`${API_URL}/api/presence/${entityType}/${entityId}`, { headers });
        if (!cancelled && r.ok) {
          const data = await r.json();
          setViewers(data.viewers || []);
        }
      } catch { /* ignore */ }
    };

    beat();
    const iv = setInterval(beat, 20_000);

    return () => {
      cancelled = true;
      clearInterval(iv);
      fetch(`${API_URL}/api/presence/${entityType}/${entityId}`, { method: "DELETE", headers }).catch(() => {});
    };
  }, [entityType, entityId]);

  return viewers;
}
