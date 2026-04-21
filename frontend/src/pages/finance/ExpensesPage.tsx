import { useGetExpensesQuery, useCreateExpenseMutation } from "../../services/api";
import { useProjectContext } from "../../shell/useProjectContext";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import { downloadCsv } from "../../shell/csvExport";

const CATEGORIES = ["labor", "materials", "equipment", "travel", "software", "consulting", "overhead", "other"];

export default function ExpensesPage() {
  const projectId = useProjectContext();
  const { data: expenses = [], refetch } = useGetExpensesQuery(projectId);
  const [createExpense] = useCreateExpenseMutation();

  return (
    <div>
      <PageHeader title="Expenses" subtitle="Approved and pending expense claims." />
      <CommandBar
        items={[
          {
            key: "new", label: "New expense", variant: "primary",
            onClick: async () => {
              const description = prompt("Description:"); if (!description) return;
              const amount = parseFloat(prompt("Amount:") || "0");
              const category = prompt(`Category (${CATEGORIES.join("/")}):`, "other") || "other";
              await createExpense({ description, amount, category, project_id: projectId });
              refetch();
            },
          },
          { key: "export", label: "Export CSV", onClick: () => downloadCsv("expenses") },
        ]}
      />
      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead><tr><th>Description</th><th>Category</th><th>Amount</th><th>Date</th><th>Approved</th></tr></thead>
          <tbody>
            {expenses.map((e: any) => (
              <tr key={e.id}>
                <td>{e.description}</td>
                <td><span className="badge badge-gray">{e.category}</span></td>
                <td style={{ fontWeight: 600 }}>${e.amount?.toLocaleString()}</td>
                <td>{e.expense_date || "-"}</td>
                <td>{e.is_approved ? <span className="badge badge-green">Yes</span> : <span className="badge badge-yellow">Pending</span>}</td>
              </tr>
            ))}
            {expenses.length === 0 && <tr><td colSpan={5} style={{ textAlign: "center", color: "var(--gray-500)", padding: "1rem" }}>No expenses.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
