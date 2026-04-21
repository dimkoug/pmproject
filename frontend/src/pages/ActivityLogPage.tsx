import { useProjectContext } from "../shell/useProjectContext";
import { useGetActivityQuery } from "../services/api";

export default function ActivityLogPage() {
  const projectId = useProjectContext();
  const { data: activities = [] } = useGetActivityQuery(projectId ?? "");

  return (
    <div>
      <div style={{ marginBottom: "1.5rem" }}>
        <h2 style={{ fontSize: "1.4rem", fontWeight: 700, marginBottom: "0.3rem" }}>Activity Log</h2>
        <p style={{ color: "var(--gray-400)", fontSize: "0.85rem" }}>Audit trail of all project changes</p>
      </div>

      {activities.length === 0 ? (
        <div className="empty-state"><p>No activity recorded yet.</p></div>
      ) : (
        <div className="card">
          {activities.map((a: any, i: number) => (
            <div key={a.id} style={{ display: "flex", gap: "0.75rem", padding: "0.65rem 0", borderBottom: i < activities.length - 1 ? "1px solid var(--gray-100)" : "none" }}>
              <div style={{ fontSize: "0.72rem", color: "var(--gray-400)", minWidth: 130, whiteSpace: "nowrap" }}>
                {new Date(a.created_at).toLocaleDateString()} {new Date(a.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </div>
              <div style={{ flex: 1, fontSize: "0.85rem" }}>
                <span style={{ fontWeight: 500, color: "var(--gray-700)" }}>{a.user_name || "System"}</span>
                {" "}
                <span className="badge badge-gray" style={{ fontSize: "0.68rem" }}>{a.action}</span>
                {" "}
                <span style={{ color: "var(--gray-600)" }}>{a.entity_type}</span>
                {a.entity_name && <span style={{ fontWeight: 500 }}> "{a.entity_name}"</span>}
                {a.details && <div style={{ fontSize: "0.78rem", color: "var(--gray-500)", marginTop: "0.15rem" }}>{a.details}</div>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
