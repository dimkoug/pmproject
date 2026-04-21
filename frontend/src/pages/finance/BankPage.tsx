import {
  useGetBankTransactionsQuery, useCreateBankTransactionMutation, useAutoMatchBankMutation,
} from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";

export default function BankPage() {
  const { data: bank = [], refetch } = useGetBankTransactionsQuery();
  const [createBank] = useCreateBankTransactionMutation();
  const [autoMatch] = useAutoMatchBankMutation();

  return (
    <div>
      <PageHeader title="Bank transactions" subtitle="Ingest bank activity and auto-match against invoices." />
      <CommandBar
        items={[
          {
            key: "auto", label: "Auto match",
            onClick: async () => {
              const r: any = await autoMatch();
              alert(`Matched ${r.data?.matched || 0}`);
              refetch();
            },
          },
          {
            key: "new", label: "New transaction", variant: "primary",
            onClick: async () => {
              const description = prompt("Description:"); if (!description) return;
              const amount = parseFloat(prompt("Amount (negative for debit):") || "0");
              await createBank({ description, amount });
              refetch();
            },
          },
        ]}
      />
      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead><tr><th>Date</th><th>Description</th><th>Amount</th><th>Reconciled</th><th>Matched invoice</th></tr></thead>
          <tbody>
            {bank.map((t: any) => (
              <tr key={t.id}>
                <td>{t.txn_date || "-"}</td>
                <td>{t.description}</td>
                <td style={{ fontWeight: 600, color: t.amount >= 0 ? "var(--success)" : "var(--danger)" }}>${t.amount?.toLocaleString()}</td>
                <td>{t.is_reconciled ? <span className="badge badge-green">Yes</span> : <span className="badge badge-gray">No</span>}</td>
                <td style={{ fontSize: "0.75rem" }}>{t.matched_invoice_id ? `${t.matched_invoice_id.slice(0, 8)}…` : "-"}</td>
              </tr>
            ))}
            {bank.length === 0 && <tr><td colSpan={5} style={{ textAlign: "center", color: "var(--gray-500)", padding: "1rem" }}>No bank transactions.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
