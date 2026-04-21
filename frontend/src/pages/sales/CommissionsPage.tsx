import {
  useGetCommissionRulesQuery, useCreateCommissionRuleMutation, useComputeCommissionsMutation,
  useGetCommissionsQuery, usePayCommissionMutation,
} from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";

export default function CommissionsPage() {
  const { data: rules = [], refetch: rRules } = useGetCommissionRulesQuery();
  const { data: commissions = [], refetch: rComm } = useGetCommissionsQuery();
  const [createRule] = useCreateCommissionRuleMutation();
  const [compute] = useComputeCommissionsMutation();
  const [pay] = usePayCommissionMutation();

  return (
    <div>
      <PageHeader title="Commissions" subtitle="Rules and payouts for sales compensation." />
      <CommandBar
        items={[
          {
            key: "compute", label: "Compute for won opps",
            onClick: async () => {
              const r: any = await compute();
              alert(`Computed ${r.data?.created || 0}`);
              rComm();
            },
          },
          {
            key: "rule", label: "New rule", variant: "primary",
            onClick: async () => {
              const name = prompt("Rule name:"); if (!name) return;
              const percentage = parseFloat(prompt("Percentage (e.g. 10):") || "0");
              await createRule({ name, percentage, min_amount: 0 });
              rRules();
            },
          },
        ]}
      />
      <div className="card">
        <h3 style={{ marginBottom: "0.75rem" }}>Rules</h3>
        <table>
          <thead><tr><th>Name</th><th>%</th><th>Min</th><th>Max</th><th>Active</th></tr></thead>
          <tbody>
            {rules.map((r: any) => (
              <tr key={r.id}>
                <td style={{ fontWeight: 500 }}>{r.name}</td>
                <td>{r.percentage}%</td>
                <td>${r.min_amount}</td>
                <td>{r.max_amount ? `$${r.max_amount}` : "—"}</td>
                <td>{r.is_active ? "Yes" : "No"}</td>
              </tr>
            ))}
            {rules.length === 0 && <tr><td colSpan={5} style={{ textAlign: "center", color: "var(--gray-500)", padding: "1rem" }}>No rules.</td></tr>}
          </tbody>
        </table>
      </div>
      <div className="card" style={{ marginTop: "1rem" }}>
        <h3 style={{ marginBottom: "0.5rem" }}>Payouts</h3>
        <table>
          <thead><tr><th>User</th><th>Base</th><th>Commission</th><th>Paid</th><th>Actions</th></tr></thead>
          <tbody>
            {commissions.map((c: any) => (
              <tr key={c.id}>
                <td style={{ fontSize: "0.75rem" }}>{c.user_id.slice(0, 8)}…</td>
                <td>${c.base_amount?.toLocaleString()}</td>
                <td style={{ fontWeight: 600 }}>${c.commission?.toLocaleString()}</td>
                <td>{c.paid ? <span className="badge badge-green">Paid</span> : <span className="badge badge-yellow">Due</span>}</td>
                <td>{!c.paid && <button className="btn btn-sm" onClick={async () => { await pay(c.id); rComm(); }}>Mark paid</button>}</td>
              </tr>
            ))}
            {commissions.length === 0 && <tr><td colSpan={5} style={{ textAlign: "center", color: "var(--gray-500)", padding: "1rem" }}>No commissions yet.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
