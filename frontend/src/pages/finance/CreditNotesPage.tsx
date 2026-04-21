import { useGetCreditNotesQuery, useCreateCreditNoteMutation } from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";

export default function CreditNotesPage() {
  const { data: creditNotes = [], refetch } = useGetCreditNotesQuery();
  const [createCN] = useCreateCreditNoteMutation();

  return (
    <div>
      <PageHeader title="Credit notes" subtitle="Adjustments issued against invoices." />
      <CommandBar
        items={[
          {
            key: "new", label: "New credit note", variant: "primary",
            onClick: async () => {
              const invoice_id = prompt("Invoice ID:"); if (!invoice_id) return;
              const cn_number = prompt("CN number:") || `CN-${Date.now().toString().slice(-6)}`;
              const amount = parseFloat(prompt("Amount:") || "0");
              const reason = prompt("Reason:") || "";
              await createCN({ invoice_id, cn_number, amount, reason });
              refetch();
            },
          },
        ]}
      />
      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead><tr><th>CN number</th><th>Invoice</th><th>Amount</th><th>Reason</th><th>Date</th></tr></thead>
          <tbody>
            {creditNotes.map((c: any) => (
              <tr key={c.id}>
                <td style={{ fontWeight: 500 }}>{c.cn_number}</td>
                <td style={{ fontSize: "0.75rem" }}>{c.invoice_id.slice(0, 8)}…</td>
                <td>${c.amount?.toLocaleString()}</td>
                <td style={{ fontSize: "0.82rem" }}>{c.reason || "-"}</td>
                <td>{c.issued_date}</td>
              </tr>
            ))}
            {creditNotes.length === 0 && <tr><td colSpan={5} style={{ textAlign: "center", color: "var(--gray-500)", padding: "1rem" }}>No credit notes.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
