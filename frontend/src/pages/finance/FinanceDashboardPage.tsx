import { useGetErpDashboardQuery } from "../../services/api";
import { useProjectContext } from "../../shell/useProjectContext";
import PageHeader from "../../shell/PageHeader";

export default function FinanceDashboardPage() {
  const projectId = useProjectContext();
  const { data: dash } = useGetErpDashboardQuery(projectId);
  if (!dash) return <div>Loading…</div>;

  return (
    <div>
      <PageHeader title="Finance dashboard" subtitle={projectId ? "Scoped to selected project." : "All-company financial snapshot."} />
      <div className="stats-grid">
        <div className="stat-card"><div className="label">Revenue</div><div className="value" style={{ color: "var(--success)" }}>${dash.revenue?.toLocaleString()}</div></div>
        <div className="stat-card"><div className="label">Expenses</div><div className="value">${dash.expenses?.total?.toLocaleString()}</div></div>
        <div className="stat-card"><div className="label">Profit</div><div className="value" style={{ color: dash.profit >= 0 ? "var(--success)" : "var(--danger)" }}>${dash.profit?.toLocaleString()}</div></div>
        <div className="stat-card"><div className="label">Invoices</div><div className="value">{dash.invoices?.count}</div></div>
        <div className="stat-card"><div className="label">Purchase orders</div><div className="value">{dash.purchase_orders?.count}</div></div>
        <div className="stat-card"><div className="label">Assets value</div><div className="value">${dash.assets?.total_value?.toLocaleString()}</div></div>
      </div>
    </div>
  );
}
