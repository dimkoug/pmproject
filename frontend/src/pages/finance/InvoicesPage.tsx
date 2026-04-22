import { useMemo } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { useGetInvoicesQuery, useCreateInvoiceMutation, useUpdateInvoiceStatusMutation, useCreateInvoiceCheckoutSessionMutation } from "../../services/api";
import { useProjectContext } from "../../shell/useProjectContext";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import DataTable from "../../shell/DataTable";
import { useDrawerPeek } from "../../shell/DetailDrawer";
import { downloadCsv } from "../../shell/csvExport";
import { promptForValues, notifyUser } from "../../shell/modalService";

const INVOICE_STATUSES = ["draft", "sent", "paid", "overdue", "cancelled"];

type Invoice = {
  id: string;
  invoice_number: string;
  invoice_type: string;
  status: string;
  total?: number;
  due_date?: string;
};

export default function InvoicesPage() {
  const projectId = useProjectContext();
  const { data: invoices = [], isLoading, refetch } = useGetInvoicesQuery(projectId);
  const [createInvoice] = useCreateInvoiceMutation();
  const [updateStatus] = useUpdateInvoiceStatusMutation();
  const [createCheckout] = useCreateInvoiceCheckoutSessionMutation();
  const { open: openPeek } = useDrawerPeek();

  const columns = useMemo<ColumnDef<Invoice, any>[]>(
    () => [
      {
        accessorKey: "invoice_number",
        header: "Number",
        cell: (c) => <span style={{ fontWeight: 500 }}>{c.getValue() as string}</span>,
      },
      {
        accessorKey: "invoice_type",
        header: "Type",
        cell: (c) => <span className="badge badge-blue">{c.getValue() as string}</span>,
      },
      {
        accessorKey: "status",
        header: "Status",
        enableSorting: false,
        cell: (c) => {
          const inv = c.row.original;
          return (
            <select
              value={inv.status}
              onClick={(e) => e.stopPropagation()}
              onChange={(e) => { updateStatus({ id: inv.id, status: e.target.value }); refetch(); }}
              style={{ fontSize: "0.8rem", padding: "0.2rem" }}
            >
              {INVOICE_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          );
        },
      },
      {
        accessorKey: "total",
        header: "Total",
        cell: (c) => {
          const v = c.getValue() as number | undefined;
          return <span style={{ fontWeight: 600 }}>${v?.toLocaleString()}</span>;
        },
      },
      {
        accessorKey: "due_date",
        header: "Due",
        cell: (c) => (c.getValue() as string) || "-",
      },
      {
        id: "actions",
        header: "Actions",
        enableSorting: false,
        cell: (c) => {
          const inv = c.row.original;
          if (inv.invoice_type !== "receivable" || inv.status === "paid") return null;
          return (
            <button
              className="btn btn-sm"
              onClick={async (e) => {
                e.stopPropagation();
                const r: any = await createCheckout(inv.id);
                if (r.error) {
                  await notifyUser({
                    title: "Stripe checkout failed",
                    description: (r.error as any)?.data?.detail || "Set STRIPE_SECRET_KEY to enable.",
                  });
                  return;
                }
                if (r.data?.url) window.open(r.data.url, "_blank", "noopener");
              }}
            >
              Pay with Stripe
            </button>
          );
        },
      },
    ],
    [updateStatus, refetch, createCheckout],
  );

  return (
    <div>
      <PageHeader title="Invoices" subtitle="Receivables and payables." />
      <CommandBar
        items={[
          {
            key: "new", label: "New invoice", variant: "primary",
            onClick: async () => {
              const v = await promptForValues({
                title: "New invoice",
                submitLabel: "Create",
                fields: [
                  { name: "invoice_number", label: "Invoice number", placeholder: `INV-${Date.now().toString().slice(-6)}` },
                  { name: "subtotal", label: "Subtotal", kind: "number", required: true, step: 0.01 },
                  { name: "tax_rate", label: "Tax rate %", kind: "number", step: 0.1 },
                ],
              });
              if (!v) return;
              const invoice_number = v.invoice_number || `INV-${Date.now().toString().slice(-6)}`;
              const subtotal = parseFloat(v.subtotal || "0");
              const tax_rate = parseFloat(v.tax_rate || "0");
              await createInvoice({ invoice_number, subtotal, tax_rate, project_id: projectId });
              refetch();
            },
          },
          { key: "export", label: "Export CSV", onClick: () => downloadCsv("invoices") },
        ]}
      />
      <DataTable
        columns={columns}
        data={invoices as Invoice[]}
        isLoading={isLoading}
        emptyTitle="No invoices yet"
        emptyDescription="Create your first invoice to start invoicing customers."
        onRowClick={(row) => openPeek("invoice", row.id)}
      />
    </div>
  );
}
