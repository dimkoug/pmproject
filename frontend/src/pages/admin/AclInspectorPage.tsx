import { useState } from "react";
import {
  useGetAdminUsersQuery,
  useGetAclPermissionsQuery,
  useInspectPermissionQuery,
  useGetProjectsQuery,
} from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import { Icon } from "../../shell/icons";

export default function AclInspectorPage() {
  const { data: users = [] } = useGetAdminUsersQuery();
  const { data: permissions = [] } = useGetAclPermissionsQuery();
  const { data: projects = [] } = useGetProjectsQuery();
  const [userId, setUserId] = useState("");
  const [codename, setCodename] = useState("");
  const [projectId, setProjectId] = useState("");

  const canQuery = !!userId && !!codename;
  const { data: result, isFetching } = useInspectPermissionQuery(
    { userId, codename, projectId: projectId || undefined },
    { skip: !canQuery }
  );

  return (
    <div>
      <PageHeader
        title="Permission Inspector"
        subtitle="Pick a user + codename (+ project, if applicable) and see exactly which rule grants or denies it."
        breadcrumbs={[{ to: "/admin", label: "Admin" }, { label: "Inspector" }]}
      />

      <div className="card">
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1rem" }}>
          <div>
            <label style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--gray-500)", textTransform: "uppercase", letterSpacing: "0.04em" }}>User</label>
            <select value={userId} onChange={(e) => setUserId(e.target.value)} style={{ width: "100%", marginTop: "0.25rem" }}>
              <option value="">— select user —</option>
              {users.map((u: any) => (
                <option key={u.id} value={u.id}>{u.name || u.email} ({u.role})</option>
              ))}
            </select>
          </div>
          <div>
            <label style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--gray-500)", textTransform: "uppercase", letterSpacing: "0.04em" }}>Codename</label>
            <select value={codename} onChange={(e) => setCodename(e.target.value)} style={{ width: "100%", marginTop: "0.25rem" }}>
              <option value="">— select permission —</option>
              {permissions.map((p: any) => (
                <option key={p.id} value={p.codename}>{p.codename} — {p.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--gray-500)", textTransform: "uppercase", letterSpacing: "0.04em" }}>Project (optional)</label>
            <select value={projectId} onChange={(e) => setProjectId(e.target.value)} style={{ width: "100%", marginTop: "0.25rem" }}>
              <option value="">— global check —</option>
              {projects.map((p: any) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {canQuery && (
        <div className="card" style={{ borderLeft: `3px solid ${result?.allowed ? "var(--success)" : "var(--danger)"}` }}>
          {isFetching ? (
            <div style={{ color: "var(--gray-500)" }}>Checking…</div>
          ) : result ? (
            <>
              <div style={{ fontSize: "1.1rem", fontWeight: 700, marginBottom: "0.75rem" }}>
                {result.allowed ? (
                  <span style={{ color: "var(--success)", display: "inline-flex", alignItems: "center", gap: "0.35rem" }}>
                    <Icon.Check size={18} /> Allowed
                  </span>
                ) : (
                  <span style={{ color: "var(--danger)", display: "inline-flex", alignItems: "center", gap: "0.35rem" }}>
                    <Icon.Close size={18} /> Denied
                  </span>
                )}
                <span style={{ fontFamily: "monospace", fontSize: "0.82rem", color: "var(--gray-500)", marginLeft: "0.75rem" }}>{result.codename}</span>
              </div>
              <div style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--gray-500)", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: "0.4rem" }}>
                Provenance
              </div>
              <ul style={{ margin: 0, paddingLeft: "1.25rem", fontSize: "0.88rem" }}>
                {result.via.map((line: string, i: number) => (
                  <li key={i} style={{ padding: "0.2rem 0" }}>{line}</li>
                ))}
              </ul>
            </>
          ) : null}
        </div>
      )}
    </div>
  );
}
