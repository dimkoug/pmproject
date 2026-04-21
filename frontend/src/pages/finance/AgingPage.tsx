import { useGetInvoiceAgingQuery, useCreatePaymentMutation } from "../../services/api";
import { useProjectContext } from "../../shell/useProjectContext";
import PageHeader from "../../shell/PageHeader";

export default function AgingPage() {
  const projectId = useProjectContext();
  const { data: aging, refetch } = useGetInvoiceAgingQuery(projectId);
  const [createPayment] = useCreatePaymentMutation();

  if (!aging) return <div>Loading…</div>;

  return (
    <div>
      <PageHeader title="Invoice aging" subtitle="Outstanding receivables bucketed by days past due." />
      <div className="stats-grid" style={{ marginBottom: "1rem" }}>
        {Object.entries(aging.buckets || {}).map(([k, v]: any) => (
          <div key={k} className="stat-card">
            <div className="label">{k.replace(/_/g, "-")} days</div>
            <div className="value">${v?.toLocaleString()}</div>
          </div>
        ))}
      </div>
      <div className="card">
        <h3 style={{ marginBottom: "0.75rem" }}>Outstanding invoices</h3>
        <table>
          <thead><tr><th>Invoice</th><th>Bucket</th><th>Due</th><th>Outstanding</th><th>Actions</th></tr></thead>
          <tbody>
            {aging.invoices?.map((i: any) => (
              <tr key={i.id}>
                <td style={{ fontWeight: 500 }}>{i.invoice_number}</td>
                <td><span className="badge badge-blue">{i.bucket}</span></td>
                <td>{i.due_date || "-"}</td>
                <td style={{ fontWeight: 600 }}>${i.outstanding?.toLocaleString()}</td>
                <td>
                  <button className="btn btn-sm" onClick={async () => {
                    const amt = parseFloat(prompt(`Payment amount (owed: $${i.outstanding}):`) || "0");
                    if (!amt) return;
                    await createPayment({ invoice_id: i.id, amount: amt });
                    refetch();
                  }}>Record payment</button>
                </td>
              </tr>
            ))}
            {(!aging.invoices || aging.invoices.length === 0) && <tr><td colSpan={5} style={{ textAlign: "center", color: "var(--gray-500)", padding: "1rem" }}>No outstanding invoices.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
