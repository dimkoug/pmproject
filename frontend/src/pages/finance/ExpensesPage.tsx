import { useMemo } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { useGetExpensesQuery, useCreateExpenseMutation } from "../../services/api";
import { useProjectContext } from "../../shell/useProjectContext";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import DataTable from "../../shell/DataTable";
import { useDrawerPeek } from "../../shell/DetailDrawer";
import { downloadCsv } from "../../shell/csvExport";
import { promptForValues } from "../../shell/modalService";

const CATEGORIES = ["labor", "materials", "equipment", "travel", "software", "consulting", "overhead", "other"];

type Expense = {
  id: string;
  description: string;
  category: string;
  amount?: number;
  expense_date?: string;
  is_approved: boolean;
};

export default function ExpensesPage() {
  const projectId = useProjectContext();
  const { data: expenses = [], isLoading, refetch } = useGetExpensesQuery(projectId);
  const [createExpense] = useCreateExpenseMutation();
  const { open: openPeek } = useDrawerPeek();

  const columns = useMemo<ColumnDef<Expense, any>[]>(
    () => [
      { accessorKey: "description", header: "Description" },
      {
        accessorKey: "category",
        header: "Category",
        cell: (c) => <span className="badge badge-gray">{c.getValue() as string}</span>,
      },
      {
        accessorKey: "amount",
        header: "Amount",
        cell: (c) => {
          const v = c.getValue() as number | undefined;
          return <span style={{ fontWeight: 600 }}>${v?.toLocaleString()}</span>;
        },
      },
      {
        accessorKey: "expense_date",
        header: "Date",
        cell: (c) => (c.getValue() as string) || "-",
      },
      {
        accessorKey: "is_approved",
        header: "Approved",
        cell: (c) =>
          c.getValue() ? (
            <span className="badge badge-green">Yes</span>
          ) : (
            <span className="badge badge-yellow">Pending</span>
          ),
      },
    ],
    [],
  );

  return (
    <div>
      <PageHeader title="Expenses" subtitle="Approved and pending expense claims." />
      <CommandBar
        items={[
          {
            key: "new", label: "New expense", variant: "primary",
            onClick: async () => {
              const v = await promptForValues({
                title: "New expense",
                submitLabel: "Create",
                fields: [
                  { name: "description", label: "Description", required: true },
                  { name: "amount", label: "Amount", kind: "number", required: true, step: 0.01 },
                  {
                    name: "category", label: "Category", kind: "select", defaultValue: "other",
                    options: CATEGORIES.map((c) => ({ value: c, label: c })),
                  },
                ],
              });
              if (!v) return;
              const amount = parseFloat(v.amount || "0");
              await createExpense({
                description: v.description,
                amount,
                category: v.category || "other",
                project_id: projectId,
              });
              refetch();
            },
          },
          { key: "export", label: "Export CSV", onClick: () => downloadCsv("expenses") },
        ]}
      />
      <DataTable
        columns={columns}
        data={expenses as Expense[]}
        isLoading={isLoading}
        emptyTitle="No expenses yet"
        emptyDescription="Log your first expense to start tracking project costs."
        onRowClick={(row) => openPeek("expense", row.id)}
      />
    </div>
  );
}
