import { useGetQuotesQuery, useCreateQuoteMutation, useConvertQuoteMutation } from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";

export default function QuotesPage() {
  const { data: quotes = [], refetch } = useGetQuotesQuery();
  const [createQuote] = useCreateQuoteMutation();
  const [convertQuote] = useConvertQuoteMutation();

  return (
    <div>
      <PageHeader title="Quotes" subtitle="Proposals that convert into invoices on acceptance." />
      <CommandBar
        items={[
          {
            key: "new", label: "New quote", variant: "primary",
            onClick: async () => {
              const num = prompt("Quote number:") || `Q-${Date.now().toString().slice(-6)}`;
              const desc = prompt("Line item description:"); if (!desc) return;
              const price = parseFloat(prompt("Unit price:") || "0");
              await createQuote({ quote_number: num, items: [{ description: desc, quantity: 1, unit_price: price }] });
              refetch();
            },
          },
        ]}
      />
      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead><tr><th>Number</th><th>Status</th><th>Total</th><th>Valid</th><th>Actions</th></tr></thead>
          <tbody>
            {quotes.map((q: any) => (
              <tr key={q.id}>
                <td style={{ fontWeight: 500 }}>{q.quote_number}</td>
                <td><span className="badge badge-blue">{q.status}</span></td>
                <td style={{ fontWeight: 600 }}>${q.total?.toLocaleString()}</td>
                <td>{q.valid_until || "-"}</td>
                <td>
                  {!q.invoice_id ? (
                    <button className="btn btn-sm" onClick={async () => { await convertQuote(q.id); refetch(); }}>Convert to invoice</button>
                  ) : (
                    <span className="badge badge-green">Converted</span>
                  )}
                </td>
              </tr>
            ))}
            {quotes.length === 0 && <tr><td colSpan={5} style={{ textAlign: "center", color: "var(--gray-500)", padding: "1rem" }}>No quotes yet.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
