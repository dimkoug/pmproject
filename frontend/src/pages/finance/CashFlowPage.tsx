import { useGetCashFlowQuery } from "../../services/api";
import PageHeader from "../../shell/PageHeader";

export default function CashFlowPage() {
  const { data: cf } = useGetCashFlowQuery();
  if (!cf) return <div>Loading…</div>;

  return (
    <div>
      <PageHeader title="Cash flow" subtitle={`Projected inflows / outflows over ${cf.horizon_days} days.`} />
      <div className="stats-grid" style={{ marginBottom: "1rem" }}>
        <div className="stat-card"><div className="label">Inflows ({cf.horizon_days}d)</div><div className="value" style={{ color: "var(--success)" }}>${cf.total_inflow?.toLocaleString()}</div></div>
        <div className="stat-card"><div className="label">Outflows</div><div className="value" style={{ color: "var(--danger)" }}>${cf.total_outflow?.toLocaleString()}</div></div>
        <div className="stat-card"><div className="label">Net</div><div className="value" style={{ color: cf.net >= 0 ? "var(--success)" : "var(--danger)" }}>${cf.net?.toLocaleString()}</div></div>
      </div>
      <div className="card">
        <table>
          <thead><tr><th>Date</th><th>Label</th><th>Amount</th><th>Running</th></tr></thead>
          <tbody>
            {cf.events?.map((e: any, i: number) => (
              <tr key={i}>
                <td>{e.date}</td>
                <td>{e.label}</td>
                <td style={{ fontWeight: 600, color: e.amount >= 0 ? "var(--success)" : "var(--danger)" }}>${e.amount?.toLocaleString()}</td>
                <td>${e.running?.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
