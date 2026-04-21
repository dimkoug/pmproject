import { useGetInvoicesQuery, useCreateInvoiceMutation, useUpdateInvoiceStatusMutation } from "../../services/api";
import { useProjectContext } from "../../shell/useProjectContext";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import { downloadCsv } from "../../shell/csvExport";

const INVOICE_STATUSES = ["draft", "sent", "paid", "overdue", "cancelled"];

export default function InvoicesPage() {
  const projectId = useProjectContext();
  const { data: invoices = [], refetch } = useGetInvoicesQuery(projectId);
  const [createInvoice] = useCreateInvoiceMutation();
  const [updateStatus] = useUpdateInvoiceStatusMutation();

  return (
    <div>
      <PageHeader title="Invoices" subtitle="Receivables and payables." />
      <CommandBar
        items={[
          {
            key: "new", label: "New invoice", variant: "primary",
            onClick: async () => {
              const invoice_number = prompt("Invoice number:") || `INV-${Date.now().toString().slice(-6)}`;
              const subtotal = parseFloat(prompt("Subtotal:") || "0");
              const tax_rate = parseFloat(prompt("Tax rate %:") || "0");
              await createInvoice({ invoice_number, subtotal, tax_rate, project_id: projectId });
              refetch();
            },
          },
          { key: "export", label: "Export CSV", onClick: () => downloadCsv("invoices") },
        ]}
      />
      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead><tr><th>Number</th><th>Type</th><th>Status</th><th>Total</th><th>Due</th></tr></thead>
          <tbody>
            {invoices.map((i: any) => (
              <tr key={i.id}>
                <td style={{ fontWeight: 500 }}>{i.invoice_number}</td>
                <td><span className="badge badge-blue">{i.invoice_type}</span></td>
                <td>
                  <select value={i.status} onChange={(e) => { updateStatus({ id: i.id, status: e.target.value }); refetch(); }} style={{ fontSize: "0.8rem", padding: "0.2rem" }}>
                    {INVOICE_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                </td>
                <td style={{ fontWeight: 600 }}>${i.total?.toLocaleString()}</td>
                <td>{i.due_date || "-"}</td>
              </tr>
            ))}
            {invoices.length === 0 && <tr><td colSpan={5} style={{ textAlign: "center", color: "var(--gray-500)", padding: "1rem" }}>No invoices.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
