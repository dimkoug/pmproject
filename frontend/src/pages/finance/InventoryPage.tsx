import { useMemo } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import {
  useGetWarehousesQuery, useCreateWarehouseMutation,
  useGetProductsQuery, useCreateProductMutation,
  useGetStockQuery, useCreateMovementMutation, useGetReorderReportQuery,
} from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import DataTable from "../../shell/DataTable";
import { useDrawerPeek } from "../../shell/DetailDrawer";
import { promptForValues, notifyUser } from "../../shell/modalService";

type Warehouse = { id: string; code: string; name: string; is_active: boolean };
type Product = { id: string; sku: string; name: string; unit_cost: number; unit_price: number; reorder_point: number };
type Stock = { sku: string; name: string; warehouse: string; quantity: number; below_reorder: boolean };

export default function InventoryPage() {
  const { data: warehouses = [], isLoading: whLoading, refetch: rWh } = useGetWarehousesQuery();
  const [createWarehouse] = useCreateWarehouseMutation();
  const { data: products = [], isLoading: prodLoading, refetch: rProd } = useGetProductsQuery();
  const [createProduct] = useCreateProductMutation();
  const { data: stock = [], isLoading: stockLoading, refetch: rStock } = useGetStockQuery();
  const [createMovement] = useCreateMovementMutation();
  const { data: reorder = [] } = useGetReorderReportQuery();
  const { open: openPeek } = useDrawerPeek();

  const warehouseColumns = useMemo<ColumnDef<Warehouse, any>[]>(
    () => [
      {
        accessorKey: "code",
        header: "Code",
        cell: (c) => <span style={{ fontWeight: 600 }}>{c.getValue() as string}</span>,
      },
      { accessorKey: "name", header: "Name" },
      {
        accessorKey: "is_active",
        header: "Active",
        cell: (c) => (c.getValue() ? "Yes" : "No"),
      },
    ],
    [],
  );

  const productColumns = useMemo<ColumnDef<Product, any>[]>(
    () => [
      {
        accessorKey: "sku",
        header: "SKU",
        cell: (c) => <span style={{ fontWeight: 600 }}>{c.getValue() as string}</span>,
      },
      { accessorKey: "name", header: "Name" },
      { accessorKey: "unit_cost", header: "Cost", cell: (c) => `$${c.getValue()}` },
      { accessorKey: "unit_price", header: "Price", cell: (c) => `$${c.getValue()}` },
      { accessorKey: "reorder_point", header: "Reorder @" },
    ],
    [],
  );

  const stockColumns = useMemo<ColumnDef<Stock, any>[]>(
    () => [
      {
        accessorKey: "sku",
        header: "SKU",
        cell: (c) => <span style={{ fontWeight: 600 }}>{c.getValue() as string}</span>,
      },
      { accessorKey: "name", header: "Name" },
      { accessorKey: "warehouse", header: "Warehouse" },
      { accessorKey: "quantity", header: "Qty" },
      {
        accessorKey: "below_reorder",
        header: "Reorder?",
        cell: (c) =>
          c.getValue() ? (
            <span className="badge badge-red">Low</span>
          ) : (
            <span className="badge badge-green">OK</span>
          ),
      },
    ],
    [],
  );

  return (
    <div>
      <PageHeader title="Inventory" subtitle="Warehouses, products, stock levels, and reorder alerts." />

      <div style={{ marginBottom: "1rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
          <h3>Warehouses</h3>
          <button className="btn btn-sm btn-primary" onClick={async () => {
            const v = await promptForValues({
              title: "New warehouse",
              submitLabel: "Create",
              fields: [
                { name: "code", label: "Code", required: true },
                { name: "name", label: "Name", placeholder: "Defaults to Code" },
              ],
            });
            if (!v) return;
            await createWarehouse({ code: v.code, name: v.name || v.code });
            rWh();
          }}>+ Warehouse</button>
        </div>
        <DataTable
          columns={warehouseColumns}
          data={warehouses as Warehouse[]}
          isLoading={whLoading}
          emptyTitle="No warehouses yet"
          emptyDescription="Add your first warehouse before tracking stock movements."
        />
      </div>

      <div style={{ marginBottom: "1rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
          <h3>Products</h3>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button className="btn btn-sm btn-primary" onClick={async () => {
              const v = await promptForValues({
                title: "New product",
                submitLabel: "Create",
                fields: [
                  { name: "sku", label: "SKU", required: true },
                  { name: "name", label: "Name", placeholder: "Defaults to SKU" },
                  { name: "unit_cost", label: "Unit cost", kind: "number", step: 0.01, defaultValue: "0" },
                  { name: "reorder_point", label: "Reorder point", kind: "number", defaultValue: "0" },
                ],
              });
              if (!v) return;
              const unit_cost = parseFloat(v.unit_cost || "0");
              const reorder_point = parseInt(v.reorder_point || "0");
              await createProduct({ sku: v.sku, name: v.name || v.sku, unit_cost, reorder_point });
              rProd();
            }}>+ Product</button>
            <button className="btn btn-sm" onClick={async () => {
              if (!products.length || !warehouses.length) {
                await notifyUser({ title: "Missing data", description: "Need product + warehouse" });
                return;
              }
              const v = await promptForValues({
                title: "New movement",
                submitLabel: "Create",
                fields: [
                  {
                    name: "movement_type", label: "Type", kind: "select", required: true, defaultValue: "receipt",
                    options: [
                      { value: "receipt", label: "Receipt" },
                      { value: "issue", label: "Issue" },
                      { value: "adjust", label: "Adjust" },
                    ],
                  },
                  { name: "quantity", label: "Quantity", kind: "number", required: true, step: 0.01 },
                ],
              });
              if (!v) return;
              const quantity = parseFloat(v.quantity || "0");
              if (!quantity) return;
              await createMovement({
                product_id: products[0].id,
                warehouse_id: warehouses[0].id,
                movement_type: v.movement_type || "receipt",
                quantity,
              });
              rStock();
            }}>+ Movement</button>
          </div>
        </div>
        <DataTable
          columns={productColumns}
          data={products as Product[]}
          isLoading={prodLoading}
          emptyTitle="No products yet"
          emptyDescription="Add a product to track SKUs and stock levels."
          onRowClick={(row) => openPeek("stock-item", row.id)}
        />
      </div>

      <div style={{ marginBottom: "1rem" }}>
        <h3 style={{ marginBottom: "0.5rem" }}>Stock levels</h3>
        <DataTable
          columns={stockColumns}
          data={stock as Stock[]}
          isLoading={stockLoading}
          emptyTitle="No stock on hand"
          emptyDescription="Record a receipt movement to populate stock levels."
          rowKey={(s, i) => `${s.sku}-${s.warehouse}-${i}`}
        />
      </div>

      {reorder.length > 0 && (
        <div className="card" style={{ marginTop: "1rem", borderLeft: "3px solid var(--danger)" }}>
          <h3 style={{ marginBottom: "0.5rem" }}>Reorder needed ({reorder.length})</h3>
          {reorder.map((r: any, i: number) => (
            <div key={i} style={{ fontSize: "0.85rem" }}>{r.sku} @ {r.warehouse}: {r.quantity}</div>
          ))}
        </div>
      )}
    </div>
  );
}
