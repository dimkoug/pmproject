import { useMemo } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { useGetInvoiceAgingQuery, useCreatePaymentMutation } from "../../services/api";
import { useProjectContext } from "../../shell/useProjectContext";
import PageHeader from "../../shell/PageHeader";
import DataTable from "../../shell/DataTable";
import { promptForValues } from "../../shell/modalService";

type AgingRow = {
  id: string;
  invoice_number: string;
  bucket: string;
  due_date?: string;
  outstanding?: number;
};

export default function AgingPage() {
  const projectId = useProjectContext();
  const { data: aging, isLoading, refetch } = useGetInvoiceAgingQuery(projectId);
  const [createPayment] = useCreatePaymentMutation();

  const columns = useMemo<ColumnDef<AgingRow, any>[]>(
    () => [
      {
        accessorKey: "invoice_number",
        header: "Invoice",
        cell: (c) => <span style={{ fontWeight: 500 }}>{c.getValue() as string}</span>,
      },
      {
        accessorKey: "bucket",
        header: "Bucket",
        cell: (c) => <span className="badge badge-blue">{c.getValue() as string}</span>,
      },
      {
        accessorKey: "due_date",
        header: "Due",
        cell: (c) => (c.getValue() as string) || "-",
      },
      {
        accessorKey: "outstanding",
        header: "Outstanding",
        cell: (c) => {
          const v = c.getValue() as number | undefined;
          return <span style={{ fontWeight: 600 }}>${v?.toLocaleString()}</span>;
        },
      },
      {
        id: "actions",
        header: "Actions",
        enableSorting: false,
        cell: (c) => {
          const i = c.row.original;
          return (
            <button
              className="btn btn-sm"
              onClick={async (e) => {
                e.stopPropagation();
                const v = await promptForValues({
                  title: "Record payment",
                  description: `Owed: $${i.outstanding}`,
                  submitLabel: "Record",
                  fields: [
                    { name: "amount", label: "Payment amount", kind: "number", required: true, step: 0.01 },
                  ],
                });
                if (!v) return;
                const amt = parseFloat(v.amount || "0");
                if (!amt) return;
                await createPayment({ invoice_id: i.id, amount: amt });
                refetch();
              }}
            >
              Record payment
            </button>
          );
        },
      },
    ],
    [createPayment, refetch],
  );

  return (
    <div>
      <PageHeader title="Invoice aging" subtitle="Outstanding receivables bucketed by days past due." />
      <div className="stats-grid" style={{ marginBottom: "1rem" }}>
        {Object.entries(aging?.buckets || {}).map(([k, v]: any) => (
          <div key={k} className="stat-card">
            <div className="label">{k.replace(/_/g, "-")} days</div>
            <div className="value">${v?.toLocaleString()}</div>
          </div>
        ))}
      </div>
      <h3 style={{ marginBottom: "0.75rem" }}>Outstanding invoices</h3>
      {/* peek omitted — aggregated view */}
      <DataTable
        columns={columns}
        data={(aging?.invoices ?? []) as AgingRow[]}
        isLoading={isLoading}
        emptyTitle="No outstanding invoices"
        emptyDescription="All invoices are paid or within their terms."
      />
    </div>
  );
}
