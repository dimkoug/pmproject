import { useMemo } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import {
  useGetSerialsQuery,
  useCreateSerialMutation,
  useUpdateSerialMutation,
  useGetProductsQuery,
  useGetWarehousesQuery,
  useGetBatchesQuery,
  useUpdateProductTrackingMutation,
} from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import DataTable from "../../shell/DataTable";
import { promptForValues, notifyUser } from "../../shell/modalService";

type Serial = {
  id: string;
  product_id: string;
  serial_no: string;
  batch_id?: string | null;
  current_warehouse_id?: string | null;
  status: string;
  received_date?: string | null;
  notes?: string | null;
};

const STATUS_BADGE: Record<string, string> = {
  in_stock: "badge-green",
  sold: "badge-blue",
  in_transit: "badge-yellow",
  scrapped: "badge-red",
  returned: "badge-gray",
};

const STATUS_OPTS = [
  { value: "in_stock", label: "In stock" },
  { value: "sold", label: "Sold" },
  { value: "in_transit", label: "In transit" },
  { value: "scrapped", label: "Scrapped" },
  { value: "returned", label: "Returned" },
];

export default function SerialsPage() {
  const { data: serials = [], isLoading, refetch } = useGetSerialsQuery();
  const { data: products = [] } = useGetProductsQuery();
  const { data: warehouses = [] } = useGetWarehousesQuery();
  const { data: batches = [] } = useGetBatchesQuery();
  const [createSerial] = useCreateSerialMutation();
  const [updateSerial] = useUpdateSerialMutation();
  const [updateTracking] = useUpdateProductTrackingMutation();

  const serialTrackedProducts = useMemo(
    () => (products as any[]).filter((p) => p.track_serial),
    [products],
  );
  const productOpts = useMemo(
    () => serialTrackedProducts.map((p) => ({ value: p.id, label: `${p.sku} · ${p.name}` })),
    [serialTrackedProducts],
  );
  const warehouseOpts = useMemo(
    () => (warehouses as any[]).map((w) => ({ value: w.id, label: `${w.code} · ${w.name}` })),
    [warehouses],
  );
  const productById = useMemo(
    () => Object.fromEntries((products as any[]).map((p) => [p.id, p])),
    [products],
  );
  const warehouseById = useMemo(
    () => Object.fromEntries((warehouses as any[]).map((w) => [w.id, w])),
    [warehouses],
  );

  const columns = useMemo<ColumnDef<Serial, any>[]>(
    () => [
      {
        accessorKey: "serial_no",
        header: "Serial #",
        cell: (c) => <span style={{ fontWeight: 500, fontFamily: "monospace" }}>{c.getValue() as string}</span>,
      },
      {
        accessorKey: "product_id",
        header: "Product",
        cell: (c) => {
          const p = productById[c.getValue() as string];
          return p ? `${p.sku} · ${p.name}` : "-";
        },
      },
      {
        accessorKey: "current_warehouse_id",
        header: "Warehouse",
        cell: (c) => {
          const v = c.getValue() as string | null | undefined;
          return v ? warehouseById[v]?.code || v.slice(0, 8) + "…" : "-";
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
        accessorKey: "received_date",
        header: "Received",
        cell: (c) => (c.getValue() as string) || "-",
      },
      {
        id: "actions",
        header: "Actions",
        enableSorting: false,
        cell: (c) => (
          <div style={{ display: "inline-flex", gap: "0.25rem" }} onClick={(e) => e.stopPropagation()}>
            <button
              className="btn btn-sm"
              onClick={async () => {
                const row = c.row.original;
                const v = await promptForValues({
                  title: `Update serial ${row.serial_no}`,
                  submitLabel: "Save",
                  fields: [
                    {
                      name: "status",
                      label: "Status",
                      required: true,
                      kind: "select",
                      options: STATUS_OPTS,
                      defaultValue: row.status,
                    },
                    {
                      name: "current_warehouse_id",
                      label: "Current warehouse (optional)",
                      kind: "select",
                      options: warehouseOpts,
                      defaultValue: row.current_warehouse_id || "",
                    },
                    { name: "notes", label: "Notes", kind: "textarea", defaultValue: row.notes || "" },
                  ],
                });
                if (!v) return;
                await updateSerial({
                  id: row.id,
                  body: {
                    status: v.status,
                    current_warehouse_id: v.current_warehouse_id || null,
                    notes: v.notes || null,
                  },
                });
                refetch();
              }}
            >
              Update
            </button>
          </div>
        ),
      },
    ],
    [updateSerial, productById, warehouseById, warehouseOpts, refetch],
  );

  return (
    <div>
      <PageHeader
        title="Serial numbers"
        subtitle="Track unit-level serialized inventory. Each status transition writes a stock movement."
      />
      <CommandBar
        items={[
          {
            key: "enable",
            label: "Enable on product",
            onClick: async () => {
              const untracked = (products as any[]).filter((p) => !p.track_serial);
              if (untracked.length === 0) {
                await notifyUser({ title: "All products are serial-tracked" });
                return;
              }
              const v = await promptForValues({
                title: "Enable serial tracking",
                submitLabel: "Enable",
                fields: [
                  {
                    name: "product_id",
                    label: "Product",
                    required: true,
                    kind: "select",
                    options: untracked.map((p) => ({ value: p.id, label: `${p.sku} · ${p.name}` })),
                  },
                ],
              });
              if (!v) return;
              await updateTracking({ productId: v.product_id, body: { track_serial: true } });
            },
          },
          {
            key: "new",
            label: "Register serial",
            variant: "primary",
            onClick: async () => {
              if (productOpts.length === 0) {
                await notifyUser({ title: "No serial-tracked products", description: "Enable serial tracking on a product first." });
                return;
              }
              const batchOpts = (batches as any[]).map((b) => ({ value: b.id, label: `${b.batch_code}` }));
              const v = await promptForValues({
                title: "Register serial",
                submitLabel: "Register",
                fields: [
                  { name: "product_id", label: "Product", required: true, kind: "select", options: productOpts },
                  { name: "serial_no", label: "Serial number", required: true },
                  { name: "current_warehouse_id", label: "Warehouse", kind: "select", options: warehouseOpts },
                  { name: "batch_id", label: "Batch (optional)", kind: "select", options: batchOpts },
                  { name: "received_date", label: "Received", kind: "date" },
                  { name: "notes", label: "Notes", kind: "textarea" },
                ],
              });
              if (!v) return;
              const r: any = await createSerial({
                product_id: v.product_id,
                serial_no: v.serial_no,
                batch_id: v.batch_id || undefined,
                current_warehouse_id: v.current_warehouse_id || undefined,
                received_date: v.received_date || undefined,
                notes: v.notes || undefined,
              });
              if (r.error) {
                await notifyUser({ title: "Failed to register serial", description: (r.error as any)?.data?.detail });
              }
              refetch();
            },
          },
        ]}
      />
      <DataTable
        columns={columns}
        data={serials as Serial[]}
        isLoading={isLoading}
        emptyTitle="No serial numbers yet"
        emptyDescription="Enable serial tracking on a product, then register individual units here."
      />
    </div>
  );
}
