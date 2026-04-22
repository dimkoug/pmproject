import { useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { useGetBudgetsQuery, useCreateBudgetMutation, useGetBudgetVarianceQuery } from "../../services/api";
import { useProjectContext } from "../../shell/useProjectContext";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import DataTable from "../../shell/DataTable";
import { useDrawerPeek } from "../../shell/DetailDrawer";
import { promptForValues } from "../../shell/modalService";

type Budget = {
  id: string;
  name: string;
  total_amount?: number;
  period_start?: string;
  period_end?: string;
};

export default function BudgetsPage() {
  const projectId = useProjectContext();
  const { data: budgets = [], isLoading, refetch } = useGetBudgetsQuery(projectId);
  const [createBudget] = useCreateBudgetMutation();
  const [selected, setSelected] = useState<string | null>(null);
  const { data: variance } = useGetBudgetVarianceQuery(selected!, { skip: !selected });
  const { open: openPeek } = useDrawerPeek();

  const columns = useMemo<ColumnDef<Budget, any>[]>(
    () => [
      {
        accessorKey: "name",
        header: "Name",
        cell: (c) => <span style={{ fontWeight: 500 }}>{c.getValue() as string}</span>,
      },
      {
        accessorKey: "total_amount",
        header: "Total",
        cell: (c) => {
          const v = c.getValue() as number | undefined;
          return `$${v?.toLocaleString() ?? 0}`;
        },
      },
      {
        id: "period",
        header: "Period",
        cell: (c) => {
          const r = c.row.original;
          return <span style={{ fontSize: "0.82rem" }}>{r.period_start || "-"} → {r.period_end || "-"}</span>;
        },
      },
      {
        id: "actions",
        header: "Actions",
        enableSorting: false,
        cell: (c) => {
          const b = c.row.original;
          return (
            <button
              className="btn btn-sm"
              onClick={(e) => {
                e.stopPropagation();
                setSelected(selected === b.id ? null : b.id);
              }}
            >
              {selected === b.id ? "Hide" : "Variance"}
            </button>
          );
        },
      },
    ],
    [selected],
  );

  return (
    <div>
      <PageHeader title="Budgets" subtitle="Track planned vs. actual spend by line item." />
      <CommandBar
        items={[
          {
            key: "new", label: "New budget", variant: "primary",
            onClick: async () => {
              const v = await promptForValues({
                title: "New budget",
                submitLabel: "Create",
                fields: [
                  { name: "name", label: "Budget name", required: true },
                  { name: "label", label: "Line item label", placeholder: "Optional" },
                  { name: "planned", label: "Planned amount", kind: "number", step: 0.01 },
                ],
              });
              if (!v) return;
              const planned = parseFloat(v.planned || "0");
              await createBudget({
                project_id: projectId,
                name: v.name,
                lines: v.label ? [{ label: v.label, planned_amount: planned }] : [],
              });
              refetch();
            },
          },
        ]}
      />
      <DataTable
        columns={columns}
        data={budgets as Budget[]}
        isLoading={isLoading}
        emptyTitle="No budgets yet"
        emptyDescription="Create your first budget to compare plan vs actual spend."
        onRowClick={(row) => openPeek("budget", row.id)}
      />
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
