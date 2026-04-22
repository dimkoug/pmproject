import { useEffect, useState } from "react";
import { useAppSelector } from "../app/hooks";

const API = (import.meta.env.VITE_API_URL as string) || "";

type Usage = {
  limits: { max_users: number; max_projects: number; max_storage_mb: number };
  usage: { users: number; projects: number; storage_mb: number };
  remaining: { users: number; projects: number; storage_mb: number };
};

/**
 * Renders plan-cap vs current-usage progress bars for a single workspace.
 * Visible to any workspace member — the backend handles permission.
 * Compact enough to sit inside the admin workspaces tab as a per-row widget
 * or at the top of a settings page.
 */
export default function WorkspaceUsageCard({ workspaceId, compact = false }: {
  workspaceId: string;
  compact?: boolean;
}) {
  const token = useAppSelector((s) => s.auth.token);
  const [data, setData] = useState<Usage | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!token || !workspaceId) return;
    (async () => {
      try {
        const r = await fetch(`${API}/api/me/workspaces/${workspaceId}/usage`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!r.ok) { setErr(`HTTP ${r.status}`); return; }
        setData(await r.json());
      } catch (e: any) {
        setErr(e?.message || "Network error");
      }
    })();
  }, [token, workspaceId]);

  if (err) return <div style={{ fontSize: "0.78rem", color: "var(--danger)" }}>Usage: {err}</div>;
  if (!data) return <div style={{ fontSize: "0.78rem", color: "var(--gray-500)" }}>Loading usage…</div>;

  const rows = [
    { label: "Users", used: data.usage.users, cap: data.limits.max_users },
    { label: "Projects", used: data.usage.projects, cap: data.limits.max_projects },
    { label: "Storage", used: data.usage.storage_mb, cap: data.limits.max_storage_mb, unit: "MB" },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: compact ? "0.35rem" : "0.5rem" }}>
      {rows.map((row) => {
        const pct = Math.min(100, Math.round((row.used / Math.max(1, row.cap)) * 100));
        const over = pct >= 100;
        const near = pct >= 80;
        const color = over ? "var(--danger)" : near ? "var(--warning)" : "var(--primary-500, #6366f1)";
        return (
          <div key={row.label}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.78rem", marginBottom: "0.15rem" }}>
              <span>{row.label}</span>
              <span style={{ color: over ? "var(--danger)" : "var(--gray-500)" }}>
                {row.used.toLocaleString()} / {row.cap.toLocaleString()} {row.unit || ""}
              </span>
            </div>
            <div style={{ height: compact ? 4 : 6, background: "var(--gray-200)", borderRadius: 99, overflow: "hidden" }}>
              <div style={{ width: `${pct}%`, height: "100%", background: color, transition: "width 0.25s ease" }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
