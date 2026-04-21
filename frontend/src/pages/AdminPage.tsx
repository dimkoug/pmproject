import { useState } from "react";
import {
  useGetApprovalsQuery, useDecideApprovalMutation,
  useGetWebhooksQuery, useCreateWebhookMutation, useDeleteWebhookMutation, useTestWebhookMutation, useGetWebhookDeliveriesQuery,
  useGetApiKeysQuery, useCreateApiKeyMutation, useRevokeApiKeyMutation,
  useGetAuditQuery,
  useGetScheduledReportsQuery, useCreateScheduledReportMutation, useRunScheduledReportsMutation,
  useGetDashboardsQuery, useCreateDashboardBuilderMutation, useDeleteDashboardMutation,
  useGetSsoProvidersQuery, useCreateSsoProviderMutation,
  useGetWorkspacesQuery, useCreateWorkspaceMutation,
} from "../services/api";

const ADMIN_TABS = ["approvals", "webhooks", "api-keys", "audit", "schedules", "dashboards", "sso", "workspaces"] as const;

export default function AdminPage() {
  const [tab, setTab] = useState<typeof ADMIN_TABS[number]>("approvals");
  const [approvalFilter, setApprovalFilter] = useState<string>("pending");
  const { data: approvals = [], refetch: rApp } = useGetApprovalsQuery({ status: approvalFilter || undefined });
  const [decide] = useDecideApprovalMutation();
  const { data: hooks = [], refetch: rHooks } = useGetWebhooksQuery(undefined, { skip: tab !== "webhooks" });
  const [createHook] = useCreateWebhookMutation();
  const [deleteHook] = useDeleteWebhookMutation();
  const [testHook] = useTestWebhookMutation();
  const [expandedHook, setExpandedHook] = useState<string | null>(null);
  const { data: deliveries = [] } = useGetWebhookDeliveriesQuery(expandedHook!, { skip: !expandedHook });
  const { data: keys = [], refetch: rKeys } = useGetApiKeysQuery(undefined, { skip: tab !== "api-keys" });
  const [createKey] = useCreateApiKeyMutation();
  const [revokeKey] = useRevokeApiKeyMutation();
  const [auditFilter, setAuditFilter] = useState("");
  const { data: auditLog = [] } = useGetAuditQuery({ domain: auditFilter || undefined }, { skip: tab !== "audit" });
  const { data: schedules = [], refetch: rSched } = useGetScheduledReportsQuery(undefined, { skip: tab !== "schedules" });
  const [createSchedule] = useCreateScheduledReportMutation();
  const [runSchedules] = useRunScheduledReportsMutation();
  const { data: dashboards = [], refetch: rDash } = useGetDashboardsQuery(undefined, { skip: tab !== "dashboards" });
  const [createDash] = useCreateDashboardBuilderMutation();
  const [deleteDash] = useDeleteDashboardMutation();
  const { data: ssoProviders = [], refetch: rSso } = useGetSsoProvidersQuery(undefined, { skip: tab !== "sso" });
  const [createSso] = useCreateSsoProviderMutation();
  const { data: workspaces = [], refetch: rWs } = useGetWorkspacesQuery(undefined, { skip: tab !== "workspaces" });
  const [createWs] = useCreateWorkspaceMutation();

  return (
    <div>
      <div style={{ marginBottom: "1.5rem" }}>
        <h2 style={{ fontSize: "1.4rem", fontWeight: 700, marginBottom: "0.3rem" }}>Admin</h2>
        <p style={{ color: "var(--gray-400)", fontSize: "0.85rem" }}>Approvals, webhooks, API keys</p>
      </div>

      <div style={{ display: "flex", gap: "0.35rem", marginBottom: "1rem", flexWrap: "wrap" }}>
        {ADMIN_TABS.map(t => <button key={t} className={`btn btn-sm ${tab === t ? "btn-primary" : ""}`} onClick={() => setTab(t)}>{t.charAt(0).toUpperCase() + t.slice(1).replace(/-/g, " ")}</button>)}
      </div>

      {tab === "approvals" && (
        <div className="card">
          <div className="card-header">
            <h3>Approval Queue</h3>
            <select value={approvalFilter} onChange={e => setApprovalFilter(e.target.value)} style={{ padding: "0.3rem 0.5rem" }}>
              <option value="">All</option><option value="pending">Pending</option>
              <option value="approved">Approved</option><option value="rejected">Rejected</option>
            </select>
          </div>
          <table><thead><tr><th>Type</th><th>Target</th><th>Status</th><th>Threshold</th><th>Note</th><th>Actions</th></tr></thead><tbody>
            {approvals.map((a: any) => <tr key={a.id}>
              <td><span className="badge badge-blue">{a.target_type}</span></td>
              <td style={{ fontSize: "0.75rem" }}>{a.target_id.slice(0, 8)}…</td>
              <td><span className={`badge ${a.status === "approved" ? "badge-green" : a.status === "rejected" ? "badge-red" : "badge-yellow"}`}>{a.status}</span></td>
              <td>{a.threshold_amount ? `$${a.threshold_amount}` : "-"}</td>
              <td style={{ fontSize: "0.82rem" }}>{a.note || "-"}</td>
              <td>{a.status === "pending" ? (
                <div style={{ display: "flex", gap: "0.25rem" }}>
                  <button className="btn btn-sm btn-primary" onClick={async () => { await decide({ id: a.id, body: { decision: "approved" } }); rApp(); }}>Approve</button>
                  <button className="btn btn-sm" onClick={async () => { const n = prompt("Reason:") || ""; await decide({ id: a.id, body: { decision: "rejected", note: n } }); rApp(); }}>Reject</button>
                </div>
              ) : <span style={{ fontSize: "0.82rem" }}>{a.decided_at ? new Date(a.decided_at).toLocaleDateString() : ""}</span>}</td>
            </tr>)}
            {approvals.length === 0 && <tr><td colSpan={6} style={{ textAlign: "center", color: "var(--gray-500)", padding: "1rem" }}>No approvals.</td></tr>}
          </tbody></table>
        </div>
      )}

      {tab === "webhooks" && (
        <>
          <div className="card">
            <div className="card-header"><h3>Webhooks</h3>
              <button className="btn btn-sm btn-primary" onClick={async () => {
                const name = prompt("Name:"); if (!name) return;
                const url = prompt("URL:"); if (!url) return;
                const events = prompt("Events (comma-sep):", "*") || "*";
                const r: any = await createHook({ name, url, events });
                if (r.data?.secret) alert(`Secret: ${r.data.secret}\nSave this — used to sign webhook payloads.`);
                rHooks();
              }}>+ New Webhook</button>
            </div>
            <table><thead><tr><th>Name</th><th>URL</th><th>Events</th><th>Active</th><th>Actions</th></tr></thead><tbody>
              {hooks.map((h: any) => <tr key={h.id}>
                <td style={{ fontWeight: 500 }}>{h.name}</td>
                <td style={{ fontSize: "0.75rem", maxWidth: 300, overflow: "hidden", textOverflow: "ellipsis" }}>{h.url}</td>
                <td style={{ fontSize: "0.78rem" }}>{h.events}</td>
                <td>{h.is_active ? <span className="badge badge-green">Yes</span> : <span className="badge badge-gray">No</span>}</td>
                <td>
                  <div style={{ display: "flex", gap: "0.25rem" }}>
                    <button className="btn btn-sm" onClick={async () => { await testHook({ id: h.id, body: { event: "test.ping", payload: { hello: "world" } } }); setTimeout(() => setExpandedHook(h.id), 500); }}>Test</button>
                    <button className="btn btn-sm" onClick={() => setExpandedHook(expandedHook === h.id ? null : h.id)}>Deliveries</button>
                    <button className="btn btn-sm" onClick={async () => { if (confirm(`Delete ${h.name}?`)) { await deleteHook(h.id); rHooks(); } }}>Delete</button>
                  </div>
                </td>
              </tr>)}
            </tbody></table>
          </div>
          {expandedHook && (
            <div className="card" style={{ marginTop: "1rem" }}>
              <h3 style={{ marginBottom: "0.75rem" }}>Recent Deliveries</h3>
              <table><thead><tr><th>Event</th><th>Status</th><th>Error</th><th>Time</th></tr></thead><tbody>
                {deliveries.map((d: any) => <tr key={d.id}>
                  <td>{d.event}</td>
                  <td><span className={`badge ${d.status_code && d.status_code < 300 ? "badge-green" : "badge-red"}`}>{d.status_code || "—"}</span></td>
                  <td style={{ fontSize: "0.75rem", color: "var(--danger)" }}>{d.error || ""}</td>
                  <td style={{ fontSize: "0.82rem" }}>{d.created_at ? new Date(d.created_at).toLocaleString() : ""}</td>
                </tr>)}
              </tbody></table>
            </div>
          )}
        </>
      )}

      {tab === "api-keys" && (
        <div className="card">
          <div className="card-header"><h3>API Keys</h3>
            <button className="btn btn-sm btn-primary" onClick={async () => {
              const name = prompt("Key name:"); if (!name) return;
              const r: any = await createKey({ name });
              if (r.data?.api_key) alert(`API key:\n${r.data.api_key}\n\n${r.data.warning}`);
              rKeys();
            }}>+ New Key</button>
          </div>
          <table><thead><tr><th>Name</th><th>Prefix</th><th>Active</th><th>Last Used</th><th>Actions</th></tr></thead><tbody>
            {keys.map((k: any) => <tr key={k.id}>
              <td style={{ fontWeight: 500 }}>{k.name}</td>
              <td style={{ fontFamily: "monospace" }}>{k.prefix}…</td>
              <td>{k.is_active ? <span className="badge badge-green">Yes</span> : <span className="badge badge-red">Revoked</span>}</td>
              <td style={{ fontSize: "0.82rem" }}>{k.last_used_at ? new Date(k.last_used_at).toLocaleDateString() : "Never"}</td>
              <td>{k.is_active && <button className="btn btn-sm" onClick={async () => { if (confirm("Revoke?")) { await revokeKey(k.id); rKeys(); } }}>Revoke</button>}</td>
            </tr>)}
          </tbody></table>
        </div>
      )}

      {tab === "audit" && (
        <div className="card">
          <div className="card-header"><h3>Audit Log</h3>
            <select value={auditFilter} onChange={e => setAuditFilter(e.target.value)} style={{ padding: "0.3rem 0.5rem" }}>
              <option value="">All domains</option>
              <option value="erp">ERP</option><option value="crm">CRM</option><option value="dms">DMS</option><option value="admin">Admin</option>
            </select>
          </div>
          <table><thead><tr><th>When</th><th>User</th><th>Domain</th><th>Action</th><th>Entity</th></tr></thead><tbody>
            {auditLog.map((a: any) => <tr key={a.id}>
              <td style={{ fontSize: "0.82rem" }}>{a.created_at ? new Date(a.created_at).toLocaleString() : ""}</td>
              <td style={{ fontSize: "0.75rem" }}>{a.user_id ? a.user_id.slice(0, 8) + "…" : "-"}</td>
              <td><span className="badge badge-blue">{a.domain}</span></td>
              <td>{a.action}</td>
              <td style={{ fontSize: "0.82rem" }}>{a.entity_type}{a.entity_id ? `:${a.entity_id.slice(0, 8)}` : ""}</td>
            </tr>)}
            {auditLog.length === 0 && <tr><td colSpan={5} style={{ textAlign: "center", color: "var(--gray-500)", padding: "1rem" }}>No entries.</td></tr>}
          </tbody></table>
        </div>
      )}

      {tab === "schedules" && (
        <div className="card">
          <div className="card-header"><h3>Scheduled Reports</h3>
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <button className="btn btn-sm" onClick={async () => { const r: any = await runSchedules(); alert(`Ran ${r.data?.ran || 0}`); rSched(); }}>Run Due</button>
              <button className="btn btn-sm btn-primary" onClick={async () => {
                const name = prompt("Report name:"); if (!name) return;
                const endpoint = prompt("Endpoint (e.g. /api/crm/dashboard):") || "";
                const freq = prompt("Frequency (daily/weekly/monthly):", "weekly") || "weekly";
                const recipients = prompt("Recipients (comma sep):") || "";
                await createSchedule({ name, endpoint, frequency: freq, recipients });
                rSched();
              }}>+ New</button>
            </div>
          </div>
          <table><thead><tr><th>Name</th><th>Endpoint</th><th>Frequency</th><th>Next Run</th><th>Recipients</th></tr></thead><tbody>
            {schedules.map((s: any) => <tr key={s.id}>
              <td style={{ fontWeight: 500 }}>{s.name}</td>
              <td style={{ fontSize: "0.75rem", fontFamily: "monospace" }}>{s.endpoint}</td>
              <td><span className="badge badge-blue">{s.frequency}</span></td>
              <td style={{ fontSize: "0.82rem" }}>{s.next_run ? new Date(s.next_run).toLocaleDateString() : ""}</td>
              <td style={{ fontSize: "0.78rem" }}>{s.recipients || "-"}</td>
            </tr>)}
          </tbody></table>
        </div>
      )}

      {tab === "dashboards" && (
        <div className="card">
          <div className="card-header"><h3>Custom Dashboards</h3>
            <button className="btn btn-sm btn-primary" onClick={async () => {
              const name = prompt("Dashboard name:"); if (!name) return;
              const widgetTitle = prompt("First widget title:") || "Widget";
              const endpoint = prompt("Widget endpoint (e.g. /api/crm/dashboard):") || "";
              const jsonPath = prompt("JSON path (e.g. pipeline_value):") || "";
              await createDash({ name, widgets: [{ title: widgetTitle, widget_type: "stat", endpoint, json_path: jsonPath, position: 0 }] });
              rDash();
            }}>+ New</button>
          </div>
          <table><thead><tr><th>Name</th><th>Shared</th><th>Owner</th><th>Actions</th></tr></thead><tbody>
            {dashboards.map((d: any) => <tr key={d.id}>
              <td style={{ fontWeight: 500 }}>{d.name}</td>
              <td>{d.is_shared ? <span className="badge badge-green">Yes</span> : <span className="badge badge-gray">No</span>}</td>
              <td style={{ fontSize: "0.75rem" }}>{d.owner_id ? d.owner_id.slice(0, 8) + "…" : "-"}</td>
              <td><button className="btn btn-sm" onClick={async () => { if (confirm("Delete?")) { await deleteDash(d.id); rDash(); } }}>Delete</button></td>
            </tr>)}
          </tbody></table>
        </div>
      )}

      {tab === "sso" && (
        <div className="card">
          <div className="card-header"><h3>SSO Providers <span style={{ fontSize: "0.75rem", color: "var(--warning)", fontWeight: 400 }}>(stub — real SSO requires OIDC/SAML library wiring)</span></h3>
            <button className="btn btn-sm btn-primary" onClick={async () => {
              const name = prompt("Provider name:"); if (!name) return;
              const issuer = prompt("OIDC issuer URL:") || "";
              const cid = prompt("Client ID:") || "";
              const cs = prompt("Client secret:") || "";
              await createSso({ name, issuer_url: issuer, client_id: cid, client_secret: cs });
              rSso();
            }}>+ New</button>
          </div>
          <table><thead><tr><th>Name</th><th>Type</th><th>Issuer</th><th>Active</th></tr></thead><tbody>
            {ssoProviders.map((p: any) => <tr key={p.id}>
              <td style={{ fontWeight: 500 }}>{p.name}</td>
              <td><span className="badge badge-blue">{p.provider_type}</span></td>
              <td style={{ fontSize: "0.75rem" }}>{p.issuer_url || "-"}</td>
              <td>{p.is_active ? "Yes" : "No"}</td>
            </tr>)}
          </tbody></table>
        </div>
      )}

      {tab === "workspaces" && (
        <div className="card">
          <div className="card-header"><h3>Workspaces <span style={{ fontSize: "0.75rem", color: "var(--warning)", fontWeight: 400 }}>(data model only — queries not yet scoped)</span></h3>
            <button className="btn btn-sm btn-primary" onClick={async () => {
              const name = prompt("Workspace name:"); if (!name) return;
              const slug = prompt("Slug (url-safe):") || name.toLowerCase().replace(/[^a-z0-9]+/g, "-");
              await createWs({ name, slug });
              rWs();
            }}>+ New</button>
          </div>
          <table><thead><tr><th>Name</th><th>Slug</th><th>Plan</th><th>Owner</th></tr></thead><tbody>
            {workspaces.map((w: any) => <tr key={w.id}>
              <td style={{ fontWeight: 500 }}>{w.name}</td>
              <td style={{ fontFamily: "monospace" }}>{w.slug}</td>
              <td><span className="badge badge-blue">{w.plan}</span></td>
              <td style={{ fontSize: "0.75rem" }}>{w.owner_id ? w.owner_id.slice(0, 8) + "…" : "-"}</td>
            </tr>)}
          </tbody></table>
        </div>
      )}
    </div>
  );
}
