import { useGetTaxReportQuery } from "../../services/api";
import PageHeader from "../../shell/PageHeader";

export default function TaxPage() {
  const { data: tax } = useGetTaxReportQuery({});
  if (!tax) return <div>Loading…</div>;

  return (
    <div>
      <PageHeader title="Tax report" subtitle="Collected vs paid, net owed, and breakdown by rate." />
      <div className="stats-grid" style={{ marginBottom: "1rem" }}>
        <div className="stat-card"><div className="label">Collected</div><div className="value">${tax.collected?.toLocaleString()}</div></div>
        <div className="stat-card"><div className="label">Paid</div><div className="value">${tax.paid?.toLocaleString()}</div></div>
        <div className="stat-card"><div className="label">Net owed</div><div className="value" style={{ color: tax.net_owed > 0 ? "var(--danger)" : "var(--success)" }}>${tax.net_owed?.toLocaleString()}</div></div>
      </div>
      <div className="card">
        <h3 style={{ marginBottom: "0.75rem" }}>By rate</h3>
        <table>
          <thead><tr><th>Rate</th><th>Taxable amount</th><th>Tax</th></tr></thead>
          <tbody>
            {tax.by_rate?.map((r: any) => (
              <tr key={r.rate}>
                <td>{r.rate}%</td>
                <td>${r.taxable?.toLocaleString()}</td>
                <td style={{ fontWeight: 600 }}>${r.tax?.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
