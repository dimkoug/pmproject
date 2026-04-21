import { useGetAccountsQuery, useCreateAccountMutation } from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";

const ACCOUNT_TYPES = ["asset", "liability", "equity", "revenue", "expense"];

export default function AccountsPage() {
  const { data: accounts = [], refetch } = useGetAccountsQuery();
  const [createAccount] = useCreateAccountMutation();

  return (
    <div>
      <PageHeader title="Chart of accounts" subtitle="General ledger accounts with running balances." />
      <CommandBar
        items={[
          {
            key: "new", label: "New account", variant: "primary",
            onClick: async () => {
              const code = prompt("Code (e.g. 1000):"); if (!code) return;
              const name = prompt("Name:"); if (!name) return;
              const account_type = prompt(`Type (${ACCOUNT_TYPES.join("/")}):`, "asset") || "asset";
              await createAccount({ code, name, account_type });
              refetch();
            },
          },
        ]}
      />
      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead><tr><th>Code</th><th>Name</th><th>Type</th><th>Balance</th></tr></thead>
          <tbody>
            {accounts.map((a: any) => (
              <tr key={a.id}>
                <td style={{ fontWeight: 600 }}>{a.code}</td>
                <td>{a.name}</td>
                <td><span className="badge badge-blue">{a.account_type}</span></td>
                <td>${a.balance?.toLocaleString()}</td>
              </tr>
            ))}
            {accounts.length === 0 && <tr><td colSpan={4} style={{ textAlign: "center", color: "var(--gray-500)", padding: "1rem" }}>No accounts.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
