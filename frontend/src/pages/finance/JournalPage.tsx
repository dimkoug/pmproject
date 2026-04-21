import {
  useGetJournalQuery, useCreateJournalMutation, usePostJournalMutation, useGetAccountsQuery,
} from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";

export default function JournalPage() {
  const { data: journal = [], refetch } = useGetJournalQuery();
  const { data: accounts = [] } = useGetAccountsQuery();
  const [createEntry] = useCreateJournalMutation();
  const [postEntry] = usePostJournalMutation();

  return (
    <div>
      <PageHeader title="Journal entries" subtitle="Manual double-entry bookkeeping." />
      <CommandBar
        items={[
          {
            key: "new", label: "New entry", variant: "primary",
            disabled: accounts.length < 2,
            title: accounts.length < 2 ? "Add at least 2 accounts first" : undefined,
            onClick: async () => {
              const entry_number = prompt("Entry #:") || `J-${Date.now().toString().slice(-6)}`;
              const amt = parseFloat(prompt("Amount:") || "0");
              if (!amt) return;
              const [debit, credit] = [accounts[0], accounts[1]];
              await createEntry({
                entry_number, memo: "Manual",
                lines: [
                  { account_id: debit.id, debit: amt, credit: 0 },
                  { account_id: credit.id, debit: 0, credit: amt },
                ],
              });
              refetch();
            },
          },
        ]}
      />
      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead><tr><th>Entry #</th><th>Date</th><th>Memo</th><th>Posted</th><th>Actions</th></tr></thead>
          <tbody>
            {journal.map((j: any) => (
              <tr key={j.id}>
                <td style={{ fontWeight: 500 }}>{j.entry_number}</td>
                <td>{j.entry_date || "-"}</td>
                <td style={{ fontSize: "0.82rem" }}>{j.memo || "-"}</td>
                <td>{j.is_posted ? <span className="badge badge-green">Yes</span> : <span className="badge badge-yellow">No</span>}</td>
                <td>{!j.is_posted && <button className="btn btn-sm" onClick={async () => { await postEntry(j.id); refetch(); }}>Post</button>}</td>
              </tr>
            ))}
            {journal.length === 0 && <tr><td colSpan={5} style={{ textAlign: "center", color: "var(--gray-500)", padding: "1rem" }}>No journal entries.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
