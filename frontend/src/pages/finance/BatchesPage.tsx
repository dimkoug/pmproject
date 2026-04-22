import { useMemo } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import {
  useGetBatchesQuery,
  useCreateBatchMutation,
  useAdjustBatchMutation,
  useGetProductsQuery,
  useGetWarehousesQuery,
  useUpdateProductTrackingMutation,
} from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import DataTable from "../../shell/DataTable";
import { Icon } from "../../shell/icons";
import { promptForValues, notifyUser } from "../../shell/modalService";

type Batch = {
  id: string;
  product_id: string;
  warehouse_id?: string | null;
  batch_code: string;
  mfg_date?: string | null;
  expiry_date?: string | null;
  qty_received: number;
  qty_on_hand: number;
  cost_per_unit?: number | null;
  notes?: string | null;
};

function daysUntil(date?: string | null): number | null {
  if (!date) return null;
  const d = new Date(date);
  const now = new Date();
  return Math.ceil((d.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
}

export default function BatchesPage() {
  const { data: batches = [], isLoading, refetch } = useGetBatchesQuery();
  const { data: products = [] } = useGetProductsQuery();
  const { data: warehouses = [] } = useGetWarehousesQuery();
  const [createBatch] = useCreateBatchMutation();
  const [adjustBatch] = useAdjustBatchMutation();
  const [updateTracking] = useUpdateProductTrackingMutation();

  const batchTrackedProducts = useMemo(
    () => (products as any[]).filter((p) => p.track_batch),
    [products],
  );
  const productOpts = useMemo(
    () => batchTrackedProducts.map((p) => ({ value: p.id, label: `${p.sku} · ${p.name}` })),
    [batchTrackedProducts],
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

  const columns = useMemo<ColumnDef<Batch, any>[]>(
    () => [
      {
        accessorKey: "batch_code",
        header: "Batch",
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
        accessorKey: "warehouse_id",
        header: "Warehouse",
        cell: (c) => {
          const v = c.getValue() as string | null | undefined;
          return v ? warehouseById[v]?.code || v.slice(0, 8) + "…" : "-";
        },
      },
      {
        accessorKey: "qty_on_hand",
        header: "On hand",
        cell: (c) => {
          const row = c.row.original;
          return (
            <span>
              <strong>{row.qty_on_hand}</strong>
              <span style={{ color: "var(--gray-400)", fontSize: "0.75rem" }}> / {row.qty_received}</span>
            </span>
          );
        },
      },
      {
        accessorKey: "expiry_date",
        header: "Expiry",
        cell: (c) => {
          const v = c.getValue() as string | null | undefined;
          if (!v) return "-";
          const d = daysUntil(v);
          const color =
            d === null
              ? "var(--gray-500)"
              : d < 0
                ? "var(--danger)"
                : d < 30
                  ? "var(--warning)"
                  : "var(--gray-700)";
          return (
            <span style={{ color }}>
              {v}
              {d !== null && (
                <span style={{ fontSize: "0.72rem", marginLeft: "0.3rem" }}>
                  {d < 0 ? `(${-d}d ago)` : `(${d}d)`}
                </span>
              )}
            </span>
          );
        },
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
                const v = await promptForValues({
                  title: `Adjust batch ${c.row.original.batch_code}`,
                  submitLabel: "Adjust",
                  fields: [
                    { name: "qty_delta", label: "Quantity delta (+/-)", required: true, kind: "number", step: 1 },
                    { name: "reason", label: "Reason", kind: "textarea" },
                  ],
                });
                if (!v) return;
                const r: any = await adjustBatch({
                  id: c.row.original.id,
                  body: { qty_delta: parseFloat(v.qty_delta || "0"), reason: v.reason || undefined },
                });
                if (r.error) {
                  await notifyUser({ title: "Adjust failed", description: (r.error as any)?.data?.detail });
                }
                refetch();
              }}
            >
              Adjust
            </button>
          </div>
        ),
      },
    ],
    [adjustBatch, productById, warehouseById, refetch],
  );

  return (
    <div>
      <PageHeader
        title="Batches / Lots"
        subtitle="Tracked batches with expiry dates. Writes inbound stock movements automatically."
      />
      <CommandBar
        items={[
          {
            key: "enable",
            label: "Enable on product",
            onClick: async () => {
              const untracked = (products as any[]).filter((p) => !p.track_batch);
              if (untracked.length === 0) {
                await notifyUser({ title: "All products are batch-tracked", description: "Create a product first or disable tracking on one to re-enable." });
                return;
              }
              const v = await promptForValues({
                title: "Enable batch tracking",
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
              await updateTracking({ productId: v.product_id, body: { track_batch: true } });
            },
          },
          {
            key: "new",
            label: "New batch",
            variant: "primary",
            onClick: async () => {
              if (productOpts.length === 0) {
                await notifyUser({ title: "No batch-tracked products", description: "Enable batch tracking on a product first." });
                return;
              }
              if (warehouseOpts.length === 0) {
                await notifyUser({ title: "No warehouses", description: "Create a warehouse first." });
                return;
              }
              const v = await promptForValues({
                title: "New batch",
                submitLabel: "Create",
                fields: [
                  { name: "product_id", label: "Product", required: true, kind: "select", options: productOpts },
                  { name: "warehouse_id", label: "Warehouse", required: true, kind: "select", options: warehouseOpts },
                  { name: "batch_code", label: "Batch code", required: true },
                  { name: "qty_received", label: "Quantity received", required: true, kind: "number", step: 1 },
                  { name: "mfg_date", label: "Manufactured", kind: "date" },
                  { name: "expiry_date", label: "Expiry", kind: "date" },
                  { name: "cost_per_unit", label: "Cost per unit", kind: "number", step: 0.01 },
                  { name: "notes", label: "Notes", kind: "textarea" },
                ],
              });
              if (!v) return;
              const r: any = await createBatch({
                product_id: v.product_id,
                warehouse_id: v.warehouse_id,
                batch_code: v.batch_code,
                qty_received: parseFloat(v.qty_received || "0"),
                mfg_date: v.mfg_date || undefined,
                expiry_date: v.expiry_date || undefined,
                cost_per_unit: v.cost_per_unit ? parseFloat(v.cost_per_unit) : undefined,
                notes: v.notes || undefined,
              });
              if (r.error) {
                await notifyUser({ title: "Failed to create batch", description: (r.error as any)?.data?.detail });
              }
              refetch();
            },
          },
        ]}
      />
      <DataTable
        columns={columns}
        data={batches as Batch[]}
        isLoading={isLoading}
        emptyTitle="No batches yet"
        emptyDescription="Enable batch tracking on a product, then record your first batch."
      />
      {batchTrackedProducts.length > 0 && (
        <div className="card" style={{ marginTop: "1rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.35rem" }}>
            <Icon.Warning size={14} color="var(--warning)" />
            <strong>Batch-tracked products</strong>
          </div>
          <div style={{ fontSize: "0.82rem", color: "var(--gray-600)" }}>
            {batchTrackedProducts.map((p) => `${p.sku} · ${p.name}`).join("  ·  ")}
          </div>
        </div>
      )}
    </div>
  );
}
