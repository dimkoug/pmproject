import { useMemo } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import {
  useGetGoodsReceiptsQuery,
  useCreateGoodsReceiptMutation,
  useConfirmGoodsReceiptMutation,
  useGetPurchaseOrdersQuery,
  useGetWarehousesQuery,
} from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import DataTable from "../../shell/DataTable";
import { useDrawerPeek } from "../../shell/DetailDrawer";
import { promptForValues, confirmAction, notifyUser } from "../../shell/modalService";

type Grn = {
  id: string;
  grn_number: string;
  po_id: string;
  warehouse_id?: string | null;
  status: string;
  received_date?: string | null;
  notes?: string | null;
};

const STATUS_BADGE: Record<string, string> = {
  draft: "badge-gray",
  confirmed: "badge-green",
  cancelled: "badge-red",
};

export default function GoodsReceiptsPage() {
  const { data: grns = [], isLoading, refetch } = useGetGoodsReceiptsQuery();
  const { data: pos = [] } = useGetPurchaseOrdersQuery();
  const { data: warehouses = [] } = useGetWarehousesQuery();
  const [createGrn] = useCreateGoodsReceiptMutation();
  const [confirmGrn] = useConfirmGoodsReceiptMutation();
  const { open: openPeek } = useDrawerPeek();

  const poOptions = useMemo(
    () => (pos as any[]).map((p) => ({ value: p.id, label: `${p.po_number} · $${(p.total_amount || 0).toLocaleString()}` })),
    [pos],
  );
  const warehouseOptions = useMemo(
    () => (warehouses as any[]).map((w) => ({ value: w.id, label: `${w.code} · ${w.name}` })),
    [warehouses],
  );

  const columns = useMemo<ColumnDef<Grn, any>[]>(
    () => [
      {
        accessorKey: "grn_number",
        header: "GRN #",
        cell: (c) => <span style={{ fontWeight: 500 }}>{c.getValue() as string}</span>,
      },
      {
        accessorKey: "po_id",
        header: "PO",
        cell: (c) => {
          const id = c.getValue() as string;
          const po = (pos as any[]).find((p) => p.id === id);
          return po ? po.po_number : id.slice(0, 8) + "…";
        },
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
        accessorKey: "received_date",
        header: "Received",
        cell: (c) => (c.getValue() as string) || "-",
      },
      {
        id: "actions",
        header: "Actions",
        enableSorting: false,
        cell: (c) => {
          const row = c.row.original;
          if (row.status !== "draft") return null;
          return (
            <div onClick={(e) => e.stopPropagation()}>
              <button
                className="btn btn-sm btn-primary"
                onClick={async () => {
                  const ok = await confirmAction({
                    title: "Confirm receipt?",
                    description: "This posts inbound stock movements and updates the PO. It cannot be undone.",
                    submitLabel: "Confirm receipt",
                  });
                  if (!ok) return;
                  const r: any = await confirmGrn(row.id);
                  if (r.error) {
                    await notifyUser({ title: "Confirm failed", description: (r.error as any)?.data?.detail || "Check warehouse and lines." });
                  }
                  refetch();
                }}
              >
                Confirm
              </button>
            </div>
          );
        },
      },
    ],
    [confirmGrn, pos, refetch],
  );

  return (
    <div>
      <PageHeader
        title="Goods receipts"
        subtitle="Record what arrived against your purchase orders. Confirming posts inbound stock movements."
      />
      <CommandBar
        items={[
          {
            key: "new",
            label: "New GRN",
            variant: "primary",
            onClick: async () => {
              if (poOptions.length === 0) {
                await notifyUser({ title: "No purchase orders", description: "Create a PO before receiving goods." });
                return;
              }
              const v = await promptForValues({
                title: "New goods receipt",
                submitLabel: "Create",
                fields: [
                  { name: "grn_number", label: "GRN number", required: true },
                  { name: "po_id", label: "Purchase order", required: true, kind: "select", options: poOptions },
                  { name: "warehouse_id", label: "Warehouse", kind: "select", options: warehouseOptions, placeholder: "Needed before confirming" },
                  { name: "description", label: "Line description", required: true },
                  { name: "quantity_received", label: "Quantity received", required: true, kind: "number", step: 1 },
                  { name: "notes", label: "Notes", kind: "textarea" },
                ],
              });
              if (!v) return;
              const r: any = await createGrn({
                grn_number: v.grn_number,
                po_id: v.po_id,
                warehouse_id: v.warehouse_id || undefined,
                notes: v.notes || undefined,
                lines: [{
                  description: v.description,
                  quantity_received: parseFloat(v.quantity_received || "0"),
                }],
              });
              if (r.error) {
                await notifyUser({ title: "Failed to create GRN", description: (r.error as any)?.data?.detail });
              }
              refetch();
            },
          },
        ]}
      />
      <DataTable
        columns={columns}
        data={grns as Grn[]}
        isLoading={isLoading}
        emptyTitle="No goods receipts yet"
        emptyDescription="Record your first delivery against a purchase order."
        onRowClick={(row) => openPeek("goods-receipt", row.id)}
      />
    </div>
  );
}
