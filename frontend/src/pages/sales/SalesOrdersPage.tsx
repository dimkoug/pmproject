import { useMemo } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import {
  useGetSalesOrdersQuery,
  useCreateSalesOrderMutation,
  useCreateSalesOrderFromQuoteMutation,
  useUpdateSalesOrderStatusMutation,
  useInvoiceSalesOrderMutation,
  useGetQuotesQuery,
  useGetCompaniesQuery,
} from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import DataTable from "../../shell/DataTable";
import { useDrawerPeek } from "../../shell/DetailDrawer";
import { promptForValues, confirmAction, notifyUser } from "../../shell/modalService";

type SalesOrder = {
  id: string;
  order_number: string;
  status: string;
  company_id?: string | null;
  quote_id?: string | null;
  invoice_id?: string | null;
  order_date?: string | null;
  delivery_date?: string | null;
  subtotal: number;
  tax_rate: number;
  total: number;
  currency: string;
};

const STATUS_BADGE: Record<string, string> = {
  draft: "badge-gray",
  confirmed: "badge-blue",
  fulfilled: "badge-yellow",
  invoiced: "badge-green",
  cancelled: "badge-red",
};

export default function SalesOrdersPage() {
  const { data: orders = [], isLoading, refetch } = useGetSalesOrdersQuery();
  const { data: quotes = [] } = useGetQuotesQuery();
  const { data: companies = [] } = useGetCompaniesQuery();
  const [createOrder] = useCreateSalesOrderMutation();
  const [fromQuote] = useCreateSalesOrderFromQuoteMutation();
  const [updateStatus] = useUpdateSalesOrderStatusMutation();
  const [invoiceIt] = useInvoiceSalesOrderMutation();
  const { open: openPeek } = useDrawerPeek();

  const companyOptions = useMemo(
    () => (companies as any[]).map((c) => ({ value: c.id, label: c.name })),
    [companies],
  );
  const quoteOptions = useMemo(
    () =>
      (quotes as any[])
        .filter((q) => ["accepted", "sent", "draft"].includes(q.status))
        .map((q) => ({ value: q.id, label: `${q.quote_number} · $${(q.total || 0).toLocaleString()}` })),
    [quotes],
  );

  const columns = useMemo<ColumnDef<SalesOrder, any>[]>(
    () => [
      {
        accessorKey: "order_number",
        header: "Order #",
        cell: (c) => <span style={{ fontWeight: 500 }}>{c.getValue() as string}</span>,
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: (c) => {
          const s = c.getValue() as string;
          return <span className={`badge ${STATUS_BADGE[s] || "badge-gray"}`}>{s}</span>;
        },
      },
      {
        accessorKey: "order_date",
        header: "Ordered",
        cell: (c) => (c.getValue() as string) || "-",
      },
      {
        accessorKey: "delivery_date",
        header: "Delivery",
        cell: (c) => (c.getValue() as string) || "-",
      },
      {
        accessorKey: "total",
        header: "Total",
        cell: (c) => {
          const v = c.getValue() as number;
          const cur = (c.row.original.currency || "USD").toUpperCase();
          return `${cur === "USD" ? "$" : cur + " "}${(v || 0).toLocaleString()}`;
        },
      },
      {
        id: "actions",
        header: "Actions",
        enableSorting: false,
        cell: (c) => {
          const row = c.row.original;
          return (
            <div style={{ display: "inline-flex", gap: "0.25rem" }} onClick={(e) => e.stopPropagation()}>
              {row.status === "draft" && (
                <button
                  className="btn btn-sm"
                  onClick={async () => {
                    await updateStatus({ id: row.id, status: "confirmed" });
                    refetch();
                  }}
                >
                  Confirm
                </button>
              )}
              {row.status === "confirmed" && (
                <button
                  className="btn btn-sm"
                  onClick={async () => {
                    await updateStatus({ id: row.id, status: "fulfilled" });
                    refetch();
                  }}
                >
                  Fulfill
                </button>
              )}
              {["confirmed", "fulfilled"].includes(row.status) && !row.invoice_id && (
                <button
                  className="btn btn-sm btn-primary"
                  onClick={async () => {
                    const ok = await confirmAction({
                      title: "Create invoice?",
                      description: `This will create an AR invoice for order ${row.order_number} and move its status to Invoiced.`,
                      submitLabel: "Create invoice",
                    });
                    if (!ok) return;
                    const r: any = await invoiceIt({ id: row.id });
                    if (r.data?.invoice_number) {
                      await notifyUser({ title: "Invoice created", description: `${r.data.invoice_number} (total $${(row.total || 0).toLocaleString()})` });
                    }
                    refetch();
                  }}
                >
                  Invoice
                </button>
              )}
            </div>
          );
        },
      },
    ],
    [updateStatus, invoiceIt, refetch],
  );

  return (
    <div>
      <PageHeader title="Sales orders" subtitle="Confirm customer commitments between Quote and Invoice." />
      <CommandBar
        items={[
          {
            key: "from-quote",
            label: "From quote",
            onClick: async () => {
              if (quoteOptions.length === 0) {
                await notifyUser({ title: "No quotes available", description: "Create a quote first to convert into an order." });
                return;
              }
              const v = await promptForValues({
                title: "Create SO from quote",
                submitLabel: "Create",
                fields: [
                  { name: "quote_id", label: "Quote", required: true, kind: "select", options: quoteOptions },
                  { name: "order_number", label: "Order number", placeholder: "Auto-generated if blank" },
                ],
              });
              if (!v) return;
              await fromQuote({ quoteId: v.quote_id, orderNumber: v.order_number || undefined });
              refetch();
            },
          },
          {
            key: "new",
            label: "New sales order",
            variant: "primary",
            onClick: async () => {
              const v = await promptForValues({
                title: "New sales order",
                submitLabel: "Create",
                fields: [
                  { name: "order_number", label: "Order number", required: true },
                  { name: "company_id", label: "Customer (optional)", kind: "select", options: companyOptions, placeholder: "Select company…" },
                  { name: "description", label: "Line description", required: true },
                  { name: "quantity", label: "Quantity", kind: "number", required: true, step: 1, defaultValue: "1" },
                  { name: "unit_price", label: "Unit price", kind: "number", required: true, step: 0.01 },
                  { name: "tax_rate", label: "Tax rate %", kind: "number", step: 0.1, defaultValue: "0" },
                  { name: "delivery_date", label: "Delivery date", kind: "date" },
                ],
              });
              if (!v) return;
              const qty = parseFloat(v.quantity || "1");
              const up = parseFloat(v.unit_price || "0");
              await createOrder({
                order_number: v.order_number,
                company_id: v.company_id || undefined,
                delivery_date: v.delivery_date || undefined,
                tax_rate: parseFloat(v.tax_rate || "0"),
                lines: [{ description: v.description, quantity: qty, unit_price: up }],
              });
              refetch();
            },
          },
        ]}
      />
      <DataTable
        columns={columns}
        data={orders as SalesOrder[]}
        isLoading={isLoading}
        emptyTitle="No sales orders yet"
        emptyDescription="Create an order or convert an accepted quote to get started."
        onRowClick={(row) => openPeek("sales-order", row.id)}
      />
    </div>
  );
}
