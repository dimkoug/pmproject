import { useGetTrialBalanceQuery } from "../../services/api";
import PageHeader from "../../shell/PageHeader";

export default function TrialBalancePage() {
  const { data: tb } = useGetTrialBalanceQuery();
  if (!tb) return <div>Loading…</div>;

  return (
    <div>
      <PageHeader title="Trial balance" subtitle="All accounts with debit and credit balances." />
      <div className="card">
        <div className="card-header">
          <h3>Trial balance</h3>
          <span>
            Debit: <b>${tb.total_debit?.toLocaleString()}</b> · Credit: <b>${tb.total_credit?.toLocaleString()}</b>{" "}
            {tb.balanced ? <span className="badge badge-green">Balanced</span> : <span className="badge badge-red">Out of balance</span>}
          </span>
        </div>
        <table>
          <thead><tr><th>Code</th><th>Name</th><th>Type</th><th>Debit</th><th>Credit</th></tr></thead>
          <tbody>
            {tb.rows?.map((r: any) => (
              <tr key={r.code}>
                <td style={{ fontWeight: 600 }}>{r.code}</td>
                <td>{r.name}</td>
                <td><span className="badge badge-gray">{r.account_type}</span></td>
                <td>{r.debit ? `$${r.debit.toLocaleString()}` : ""}</td>
                <td>{r.credit ? `$${r.credit.toLocaleString()}` : ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
