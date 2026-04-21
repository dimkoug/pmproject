import { useGetPnlQuery } from "../../services/api";
import PageHeader from "../../shell/PageHeader";

export default function PnlPage() {
  const { data: pnl } = useGetPnlQuery({});
  if (!pnl) return <div>Loading…</div>;

  return (
    <div>
      <PageHeader title="Profit & Loss" subtitle="Revenue, expenses, and net income." />
      <div className="stats-grid" style={{ marginBottom: "1rem" }}>
        <div className="stat-card"><div className="label">Revenue</div><div className="value" style={{ color: "var(--success)" }}>${pnl.revenue?.toLocaleString()}</div></div>
        <div className="stat-card"><div className="label">Expenses</div><div className="value">${pnl.expenses?.toLocaleString()}</div></div>
        <div className="stat-card"><div className="label">Net income</div><div className="value" style={{ color: pnl.net_income >= 0 ? "var(--success)" : "var(--danger)" }}>${pnl.net_income?.toLocaleString()}</div></div>
      </div>
      <div className="card">
        <h3 style={{ marginBottom: "0.75rem" }}>Accounts</h3>
        <table>
          <thead><tr><th>Code</th><th>Name</th><th>Type</th><th>Balance</th></tr></thead>
          <tbody>
            {pnl.accounts?.map((a: any) => (
              <tr key={a.code}>
                <td style={{ fontWeight: 600 }}>{a.code}</td>
                <td>{a.name}</td>
                <td><span className="badge badge-blue">{a.type}</span></td>
                <td>${a.balance?.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
