import { useState } from "react";
import { useGetBudgetsQuery, useCreateBudgetMutation, useGetBudgetVarianceQuery } from "../../services/api";
import { useProjectContext } from "../../shell/useProjectContext";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";

export default function BudgetsPage() {
  const projectId = useProjectContext();
  const { data: budgets = [], refetch } = useGetBudgetsQuery(projectId);
  const [createBudget] = useCreateBudgetMutation();
  const [selected, setSelected] = useState<string | null>(null);
  const { data: variance } = useGetBudgetVarianceQuery(selected!, { skip: !selected });

  return (
    <div>
      <PageHeader title="Budgets" subtitle="Track planned vs. actual spend by line item." />
      <CommandBar
        items={[
          {
            key: "new", label: "New budget", variant: "primary",
            onClick: async () => {
              const name = prompt("Budget name:"); if (!name) return;
              const label = prompt("Line item label:");
              const planned = parseFloat(prompt("Planned amount:") || "0");
              await createBudget({ project_id: projectId, name, lines: label ? [{ label, planned_amount: planned }] : [] });
              refetch();
            },
          },
        ]}
      />
      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead><tr><th>Name</th><th>Total</th><th>Period</th><th>Actions</th></tr></thead>
          <tbody>
            {budgets.map((b: any) => (
              <tr key={b.id}>
                <td style={{ fontWeight: 500 }}>{b.name}</td>
                <td>${b.total_amount?.toLocaleString()}</td>
                <td style={{ fontSize: "0.82rem" }}>{b.period_start || "-"} → {b.period_end || "-"}</td>
                <td>
                  <button className="btn btn-sm" onClick={() => setSelected(selected === b.id ? null : b.id)}>
                    {selected === b.id ? "Hide" : "Variance"}
                  </button>
                </td>
              </tr>
            ))}
            {budgets.length === 0 && <tr><td colSpan={4} style={{ textAlign: "center", color: "var(--gray-500)", padding: "1rem" }}>No budgets.</td></tr>}
          </tbody>
        </table>
      </div>
      {variance && (
        <div className="card" style={{ marginTop: "1rem" }}>
          <div className="card-header">
            <h3>Variance</h3>
            <div>
              Planned: <b>${variance.total_planned?.toLocaleString()}</b> · Actual: <b>${variance.total_actual?.toLocaleString()}</b> · Variance:{" "}
              <b style={{ color: variance.total_variance >= 0 ? "var(--success)" : "var(--danger)" }}>${variance.total_variance?.toLocaleString()}</b>
            </div>
          </div>
          <table>
            <thead><tr><th>Line</th><th>Category</th><th>Planned</th><th>Actual</th><th>Variance</th><th>% used</th></tr></thead>
            <tbody>
              {variance.lines?.map((l: any) => (
                <tr key={l.line_id}>
                  <td>{l.label}</td>
                  <td>{l.category || "-"}</td>
                  <td>${l.planned?.toLocaleString()}</td>
                  <td>${l.actual?.toLocaleString()}</td>
                  <td style={{ color: l.variance >= 0 ? "var(--success)" : "var(--danger)", fontWeight: 600 }}>${l.variance?.toLocaleString()}</td>
                  <td>{l.pct_used}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
