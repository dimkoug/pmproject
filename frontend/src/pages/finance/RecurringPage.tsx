import { useMemo } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import {
  useGetRecurringInvoicesQuery, useCreateRecurringInvoiceMutation, useRunRecurringInvoicesMutation,
} from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import DataTable from "../../shell/DataTable";
import { useDrawerPeek } from "../../shell/DetailDrawer";
import { promptForValues, notifyUser } from "../../shell/modalService";

type Recurring = {
  id: string;
  template_name: string;
  amount?: number;
  frequency: string;
  next_run?: string;
  is_active: boolean;
};

export default function RecurringPage() {
  const { data: recurring = [], isLoading, refetch } = useGetRecurringInvoicesQuery();
  const [createRec] = useCreateRecurringInvoiceMutation();
  const [runRec] = useRunRecurringInvoicesMutation();
  const { open: openPeek } = useDrawerPeek();

  const columns = useMemo<ColumnDef<Recurring, any>[]>(
    () => [
      {
        accessorKey: "template_name",
        header: "Template",
        cell: (c) => <span style={{ fontWeight: 500 }}>{c.getValue() as string}</span>,
      },
      {
        accessorKey: "amount",
        header: "Amount",
        cell: (c) => {
          const v = c.getValue() as number | undefined;
          return `$${v?.toLocaleString() ?? 0}`;
        },
      },
      {
        accessorKey: "frequency",
        header: "Frequency",
        cell: (c) => <span className="badge badge-blue">{c.getValue() as string}</span>,
      },
      {
        accessorKey: "next_run",
        header: "Next run",
        cell: (c) => (c.getValue() as string) || "-",
      },
      {
        accessorKey: "is_active",
        header: "Active",
        cell: (c) =>
          c.getValue() ? (
            <span className="badge badge-green">Yes</span>
          ) : (
            <span className="badge badge-gray">No</span>
          ),
      },
    ],
    [],
  );

  return (
    <div>
      <PageHeader title="Recurring invoices" subtitle="Templates that auto-generate invoices on a schedule." />
      <CommandBar
        items={[
          {
            key: "run", label: "Run due now",
            onClick: async () => {
              const r: any = await runRec();
              await notifyUser({ title: "Recurring run complete", description: `Generated ${r.data?.count || 0}` });
              refetch();
            },
          },
          {
            key: "new", label: "New template", variant: "primary",
            onClick: async () => {
              const v = await promptForValues({
                title: "New recurring template",
                submitLabel: "Create",
                fields: [
                  { name: "template_name", label: "Template name", required: true },
                  { name: "amount", label: "Amount", kind: "number", required: true, step: 0.01 },
                  {
                    name: "frequency", label: "Frequency", kind: "select", defaultValue: "monthly",
                    options: [
                      { value: "weekly", label: "Weekly" },
                      { value: "monthly", label: "Monthly" },
                      { value: "quarterly", label: "Quarterly" },
                      { value: "yearly", label: "Yearly" },
                    ],
                  },
                ],
              });
              if (!v) return;
              const amount = parseFloat(v.amount || "0");
              await createRec({
                template_name: v.template_name,
                amount,
                frequency: v.frequency || "monthly",
              });
              refetch();
            },
          },
        ]}
      />
      <DataTable
        columns={columns}
        data={recurring as Recurring[]}
        isLoading={isLoading}
        emptyTitle="No recurring templates yet"
        emptyDescription="Create a template to auto-generate invoices on a schedule."
        onRowClick={(row) => openPeek("recurring-invoice", row.id)}
      />
    </div>
  );
}
