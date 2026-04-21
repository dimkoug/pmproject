import {
  useGetRecurringInvoicesQuery, useCreateRecurringInvoiceMutation, useRunRecurringInvoicesMutation,
} from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";

export default function RecurringPage() {
  const { data: recurring = [], refetch } = useGetRecurringInvoicesQuery();
  const [createRec] = useCreateRecurringInvoiceMutation();
  const [runRec] = useRunRecurringInvoicesMutation();

  return (
    <div>
      <PageHeader title="Recurring invoices" subtitle="Templates that auto-generate invoices on a schedule." />
      <CommandBar
        items={[
          {
            key: "run", label: "Run due now",
            onClick: async () => {
              const r: any = await runRec();
              alert(`Generated ${r.data?.count || 0}`);
              refetch();
            },
          },
          {
            key: "new", label: "New template", variant: "primary",
            onClick: async () => {
              const template_name = prompt("Template name:"); if (!template_name) return;
              const amount = parseFloat(prompt("Amount:") || "0");
              const frequency = prompt("Frequency (weekly/monthly/quarterly/yearly):", "monthly") || "monthly";
              await createRec({ template_name, amount, frequency });
              refetch();
            },
          },
        ]}
      />
      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead><tr><th>Template</th><th>Amount</th><th>Frequency</th><th>Next run</th><th>Active</th></tr></thead>
          <tbody>
            {recurring.map((r: any) => (
              <tr key={r.id}>
                <td style={{ fontWeight: 500 }}>{r.template_name}</td>
                <td>${r.amount?.toLocaleString()}</td>
                <td><span className="badge badge-blue">{r.frequency}</span></td>
                <td>{r.next_run || "-"}</td>
                <td>{r.is_active ? <span className="badge badge-green">Yes</span> : <span className="badge badge-gray">No</span>}</td>
              </tr>
            ))}
            {recurring.length === 0 && <tr><td colSpan={5} style={{ textAlign: "center", color: "var(--gray-500)", padding: "1rem" }}>No templates.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
