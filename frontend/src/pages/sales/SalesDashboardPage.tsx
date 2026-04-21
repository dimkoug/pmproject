import { useGetCrmDashboardQuery } from "../../services/api";
import PageHeader from "../../shell/PageHeader";

export default function SalesDashboardPage() {
  const { data: dash } = useGetCrmDashboardQuery();
  if (!dash) return <div>Loading…</div>;

  return (
    <div>
      <PageHeader title="Sales dashboard" subtitle="CRM overview — companies, pipeline, won revenue." />
      <div className="stats-grid">
        <div className="stat-card"><div className="label">Companies</div><div className="value">{dash.companies}</div></div>
        <div className="stat-card"><div className="label">Contacts</div><div className="value">{dash.contacts}</div></div>
        <div className="stat-card"><div className="label">Active leads</div><div className="value">{dash.active_leads}</div></div>
        <div className="stat-card"><div className="label">Open opportunities</div><div className="value">{dash.open_opportunities}</div></div>
        <div className="stat-card"><div className="label">Pipeline value</div><div className="value">${dash.pipeline_value?.toLocaleString()}</div></div>
        <div className="stat-card"><div className="label">Won revenue</div><div className="value" style={{ color: "var(--success)" }}>${dash.won_value?.toLocaleString()}</div></div>
      </div>
      {dash.pipeline_by_stage?.length > 0 && (
        <div className="card">
          <h3 style={{ marginBottom: "0.75rem" }}>Pipeline by stage</h3>
          <table>
            <thead><tr><th>Stage</th><th>Count</th><th>Value</th></tr></thead>
            <tbody>
              {dash.pipeline_by_stage.map((s: any) => (
                <tr key={s.stage}>
                  <td><span className="badge badge-blue">{s.stage.replace(/_/g, " ")}</span></td>
                  <td>{s.count}</td>
                  <td>${s.value?.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
