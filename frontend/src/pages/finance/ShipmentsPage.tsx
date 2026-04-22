import { useMemo } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import {
  useGetShipmentsQuery,
  useCreateShipmentMutation,
  useUpdateShipmentStatusMutation,
  useGetCarriersQuery,
  useGetSalesOrdersQuery,
  useGetInvoicesQuery,
} from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import DataTable from "../../shell/DataTable";
import { promptForValues, notifyUser } from "../../shell/modalService";
import { useFormat } from "../../i18n/format";

type Shipment = {
  id: string;
  sales_order_id?: string | null;
  invoice_id?: string | null;
  carrier: string;
  tracking_number: string;
  status: string;
  shipped_date?: string | null;
  delivered_date?: string | null;
  expected_delivery?: string | null;
  notes?: string | null;
};

const STATUS_BADGE: Record<string, string> = {
  pending: "badge-gray",
  label_created: "badge-blue",
  in_transit: "badge-yellow",
  delivered: "badge-green",
  exception: "badge-red",
  cancelled: "badge-gray",
};

const STATUS_OPTS = [
  { value: "pending", label: "Pending" },
  { value: "label_created", label: "Label created" },
  { value: "in_transit", label: "In transit" },
  { value: "delivered", label: "Delivered" },
  { value: "exception", label: "Exception" },
  { value: "cancelled", label: "Cancelled" },
];

export default function ShipmentsPage() {
  const { data: shipments = [], isLoading, refetch } = useGetShipmentsQuery();
  const { data: carriers = [] } = useGetCarriersQuery();
  const { data: salesOrders = [] } = useGetSalesOrdersQuery();
  const { data: invoices = [] } = useGetInvoicesQuery();
  const [createShipment] = useCreateShipmentMutation();
  const [updateStatus] = useUpdateShipmentStatusMutation();
  const { formatDate } = useFormat();

  const soOpts = useMemo(
    () => (salesOrders as any[]).map((s) => ({ value: s.id, label: `${s.order_number} · ${s.status}` })),
    [salesOrders],
  );
  const invOpts = useMemo(
    () => (invoices as any[]).map((i) => ({ value: i.id, label: `${i.invoice_number} · $${(i.total || 0).toLocaleString()}` })),
    [invoices],
  );
  const soByIdLabel = useMemo(
    () => Object.fromEntries((salesOrders as any[]).map((s) => [s.id, s.order_number])),
    [salesOrders],
  );
  const invByIdLabel = useMemo(
    () => Object.fromEntries((invoices as any[]).map((i) => [i.id, i.invoice_number])),
    [invoices],
  );

  const columns = useMemo<ColumnDef<Shipment, any>[]>(
    () => [
      {
        accessorKey: "carrier",
        header: "Carrier",
        cell: (c) => <span className="badge badge-gray" style={{ textTransform: "uppercase" }}>{c.getValue() as string}</span>,
      },
      {
        accessorKey: "tracking_number",
        header: "Tracking #",
        cell: (c) => <code style={{ fontSize: "0.78rem" }}>{c.getValue() as string}</code>,
      },
      {
        id: "attached_to",
        header: "Attached to",
        cell: (c) => {
          const r = c.row.original;
          if (r.sales_order_id) return <span>SO {soByIdLabel[r.sales_order_id] || r.sales_order_id.slice(0, 8) + "…"}</span>;
          if (r.invoice_id) return <span>INV {invByIdLabel[r.invoice_id] || r.invoice_id.slice(0, 8) + "…"}</span>;
          return "—";
        },
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: (c) => {
          const s = c.getValue() as string;
          return <span className={`badge ${STATUS_BADGE[s] || "badge-gray"}`}>{s.replace("_", " ")}</span>;
        },
      },
      {
        accessorKey: "shipped_date",
        header: "Shipped",
        cell: (c) => formatDate(c.getValue() as string | undefined),
      },
      {
        accessorKey: "delivered_date",
        header: "Delivered",
        cell: (c) => formatDate(c.getValue() as string | undefined),
      },
      {
        id: "actions",
        header: "Actions",
        enableSorting: false,
        cell: (c) => {
          const row = c.row.original;
          if (row.status === "delivered" || row.status === "cancelled") return null;
          return (
            <div style={{ display: "inline-flex", gap: "0.25rem" }} onClick={(e) => e.stopPropagation()}>
              <button
                className="btn btn-sm"
                onClick={async () => {
                  const v = await promptForValues({
                    title: `Update status — ${row.tracking_number}`,
                    submitLabel: "Save",
                    fields: [
                      { name: "status", label: "Status", required: true, kind: "select", options: STATUS_OPTS, defaultValue: row.status },
                      { name: "delivered_date", label: "Delivered date (optional)", kind: "date" },
                      { name: "notes", label: "Notes", kind: "textarea" },
                    ],
                  });
                  if (!v) return;
                  await updateStatus({
                    id: row.id,
                    body: {
                      status: v.status,
                      delivered_date: v.delivered_date || null,
                      notes: v.notes || null,
                    },
                  });
                  refetch();
                }}
              >
                Update
              </button>
            </div>
          );
        },
      },
    ],
    [updateStatus, refetch, soByIdLabel, invByIdLabel, formatDate],
  );

  return (
    <div>
      <PageHeader
        title="Shipments"
        subtitle="Track outbound deliveries against sales orders or invoices. Carrier-side label printing is stub-only — wire a real adapter in app/routers/shipping.py."
      />
      <CommandBar
        items={[
          {
            key: "new",
            label: "New shipment",
            variant: "primary",
            onClick: async () => {
              if (carriers.length === 0) {
                await notifyUser({ title: "No carriers loaded" });
                return;
              }
              const v = await promptForValues({
                title: "New shipment",
                submitLabel: "Create",
                fields: [
                  { name: "carrier", label: "Carrier", required: true, kind: "select", options: carriers },
                  { name: "tracking_number", label: "Tracking number", required: true },
                  { name: "sales_order_id", label: "Sales order (optional)", kind: "select", options: soOpts },
                  { name: "invoice_id", label: "Invoice (optional)", kind: "select", options: invOpts },
                  { name: "shipped_date", label: "Shipped date", kind: "date" },
                  { name: "expected_delivery", label: "Expected delivery", kind: "date" },
                  { name: "notes", label: "Notes", kind: "textarea" },
                ],
              });
              if (!v) return;
              if (!v.sales_order_id && !v.invoice_id) {
                await notifyUser({ title: "Attachment required", description: "Pick a sales order or invoice." });
                return;
              }
              const r: any = await createShipment({
                carrier: v.carrier,
                tracking_number: v.tracking_number,
                sales_order_id: v.sales_order_id || undefined,
                invoice_id: v.invoice_id || undefined,
                shipped_date: v.shipped_date || undefined,
                expected_delivery: v.expected_delivery || undefined,
                notes: v.notes || undefined,
              });
              if (r.error) {
                await notifyUser({ title: "Create failed", description: (r.error as any)?.data?.detail });
              }
            },
          },
        ]}
      />
      <DataTable
        columns={columns}
        data={shipments as Shipment[]}
        isLoading={isLoading}
        emptyTitle="No shipments yet"
        emptyDescription="Attach a tracking number to a sales order or invoice to start tracking deliveries."
      />
    </div>
  );
}
