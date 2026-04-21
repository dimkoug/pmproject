import { useState } from "react";
import { useGetDmsUsageReportQuery, useGetAdminUsersQuery } from "../../services/api";
import PageHeader from "../../shell/PageHeader";

export default function UsageReportPage() {
  const [days, setDays] = useState(30);
  const { data: report } = useGetDmsUsageReportQuery(days);
  const { data: users = [] } = useGetAdminUsersQuery();

  const userLabel = (uid: string | null) => {
    if (!uid) return "(unknown)";
    const u = users.find((x: any) => x.id === uid);
    return u ? (u.name || u.email) : uid.slice(0, 8) + "…";
  };

  return (
    <div>
      <PageHeader
        title="Usage report"
        subtitle="Top downloaders and most-accessed documents, from the DMS audit log."
        breadcrumbs={[{ to: "/documents", label: "Documents" }, { label: "Reports" }, { label: "Usage" }]}
      />
      <div className="card" style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
        <label style={{ fontSize: "0.82rem" }}>Window</label>
        <select value={days} onChange={(e) => setDays(Number(e.target.value))}>
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
          <option value={365}>Last year</option>
        </select>
      </div>

      {!report ? <div>Loading…</div> : (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
          <div className="card">
            <h3 style={{ marginBottom: "0.75rem" }}>Top users</h3>
            <table>
              <thead><tr><th>User</th><th style={{ textAlign: "right" }}>Actions</th></tr></thead>
              <tbody>
                {report.top_users?.map((u: any) => (
                  <tr key={u.user_id || "null"}>
                    <td>{userLabel(u.user_id)}</td>
                    <td style={{ textAlign: "right", fontWeight: 600 }}>{u.actions}</td>
                  </tr>
                ))}
                {(!report.top_users || report.top_users.length === 0) && (
                  <tr><td colSpan={2} style={{ textAlign: "center", color: "var(--gray-500)", padding: "1rem" }}>No activity in window.</td></tr>
                )}
              </tbody>
            </table>
          </div>
          <div className="card">
            <h3 style={{ marginBottom: "0.75rem" }}>Top documents</h3>
            <table>
              <thead><tr><th>Document</th><th style={{ textAlign: "right" }}>Actions</th></tr></thead>
              <tbody>
                {report.top_documents?.map((d: any) => (
                  <tr key={d.document_id}>
                    <td>{d.title || (d.document_id || "—").slice(0, 8) + "…"}</td>
                    <td style={{ textAlign: "right", fontWeight: 600 }}>{d.actions}</td>
                  </tr>
                ))}
                {(!report.top_documents || report.top_documents.length === 0) && (
                  <tr><td colSpan={2} style={{ textAlign: "center", color: "var(--gray-500)", padding: "1rem" }}>No activity in window.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
