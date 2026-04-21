import {
  useGetContractsQuery, useCreateContractMutation, useGetContractMetricsQuery,
  useUpdateContractStatusMutation, useGetCompaniesQuery,
} from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";

const CONTRACT_STATUSES = ["draft", "active", "renewing", "churned", "expired"];

export default function ContractsPage() {
  const { data: contracts = [], refetch } = useGetContractsQuery();
  const { data: metrics } = useGetContractMetricsQuery();
  const { data: companies = [] } = useGetCompaniesQuery();
  const [createContract] = useCreateContractMutation();
  const [updateStatus] = useUpdateContractStatusMutation();

  return (
    <div>
      <PageHeader title="Contracts" subtitle="Active customer agreements with MRR and ARR metrics." />
      <CommandBar
        items={[
          {
            key: "new", label: "New contract", variant: "primary",
            onClick: async () => {
              if (!companies.length) { alert("Add a company first"); return; }
              const num = prompt("Contract #:") || `C-${Date.now().toString().slice(-6)}`;
              const amt = parseFloat(prompt("Amount:") || "0");
              const cycle = prompt("Billing (monthly/quarterly/yearly/one_time):", "monthly") || "monthly";
              const start = prompt("Start date (YYYY-MM-DD):", new Date().toISOString().slice(0, 10)) || "";
              await createContract({
                company_id: companies[0].id, contract_number: num,
                amount: amt, billing_cycle: cycle, start_date: start, status: "active",
              });
              refetch();
            },
          },
        ]}
      />
      {metrics && (
        <div className="stats-grid" style={{ marginBottom: "1rem" }}>
          <div className="stat-card"><div className="label">Active</div><div className="value">{metrics.active_count}</div></div>
          <div className="stat-card"><div className="label">MRR</div><div className="value">${metrics.mrr?.toLocaleString()}</div></div>
          <div className="stat-card"><div className="label">ARR</div><div className="value" style={{ color: "var(--success)" }}>${metrics.arr?.toLocaleString()}</div></div>
          <div className="stat-card"><div className="label">Renewals ≤30d</div><div className="value" style={{ color: metrics.renewals_due_30d?.length ? "var(--warning)" : "inherit" }}>{metrics.renewals_due_30d?.length || 0}</div></div>
          <div className="stat-card"><div className="label">Churned</div><div className="value" style={{ color: "var(--danger)" }}>{metrics.churned_total}</div></div>
        </div>
      )}
      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead><tr><th>Number</th><th>Status</th><th>Cycle</th><th>Amount</th><th>MRR</th><th>Dates</th></tr></thead>
          <tbody>
            {contracts.map((c: any) => (
              <tr key={c.id}>
                <td style={{ fontWeight: 500 }}>{c.contract_number}</td>
                <td>
                  <select value={c.status} onChange={(e) => { updateStatus({ id: c.id, status: e.target.value }); refetch(); }} style={{ fontSize: "0.8rem", padding: "0.2rem" }}>
                    {CONTRACT_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                </td>
                <td><span className="badge badge-blue">{c.billing_cycle}</span></td>
                <td style={{ fontWeight: 600 }}>${c.amount?.toLocaleString()}</td>
                <td>${c.mrr?.toLocaleString()}</td>
                <td style={{ fontSize: "0.82rem" }}>{c.start_date} → {c.end_date || "—"}</td>
              </tr>
            ))}
            {contracts.length === 0 && <tr><td colSpan={6} style={{ textAlign: "center", color: "var(--gray-500)", padding: "1rem" }}>No contracts.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
