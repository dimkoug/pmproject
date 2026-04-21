import {
  useGetWarehousesQuery, useCreateWarehouseMutation,
  useGetProductsQuery, useCreateProductMutation,
  useGetStockQuery, useCreateMovementMutation, useGetReorderReportQuery,
} from "../../services/api";
import PageHeader from "../../shell/PageHeader";

export default function InventoryPage() {
  const { data: warehouses = [], refetch: rWh } = useGetWarehousesQuery();
  const [createWarehouse] = useCreateWarehouseMutation();
  const { data: products = [], refetch: rProd } = useGetProductsQuery();
  const [createProduct] = useCreateProductMutation();
  const { data: stock = [], refetch: rStock } = useGetStockQuery();
  const [createMovement] = useCreateMovementMutation();
  const { data: reorder = [] } = useGetReorderReportQuery();

  return (
    <div>
      <PageHeader title="Inventory" subtitle="Warehouses, products, stock levels, and reorder alerts." />

      <div className="card">
        <div className="card-header">
          <h3>Warehouses</h3>
          <button className="btn btn-sm btn-primary" onClick={async () => {
            const code = prompt("Code:"); if (!code) return;
            const name = prompt("Name:") || code;
            await createWarehouse({ code, name }); rWh();
          }}>+ Warehouse</button>
        </div>
        <table>
          <thead><tr><th>Code</th><th>Name</th><th>Active</th></tr></thead>
          <tbody>
            {warehouses.map((w: any) => (
              <tr key={w.id}>
                <td style={{ fontWeight: 600 }}>{w.code}</td>
                <td>{w.name}</td>
                <td>{w.is_active ? "Yes" : "No"}</td>
              </tr>
            ))}
            {warehouses.length === 0 && <tr><td colSpan={3} style={{ textAlign: "center", color: "var(--gray-500)", padding: "1rem" }}>No warehouses.</td></tr>}
          </tbody>
        </table>
      </div>

      <div className="card" style={{ marginTop: "1rem" }}>
        <div className="card-header">
          <h3>Products</h3>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button className="btn btn-sm btn-primary" onClick={async () => {
              const sku = prompt("SKU:"); if (!sku) return;
              const name = prompt("Name:") || sku;
              const unit_cost = parseFloat(prompt("Unit cost:") || "0");
              const reorder_point = parseInt(prompt("Reorder point:") || "0");
              await createProduct({ sku, name, unit_cost, reorder_point });
              rProd();
            }}>+ Product</button>
            <button className="btn btn-sm" onClick={async () => {
              if (!products.length || !warehouses.length) { alert("Need product + warehouse"); return; }
              const movement_type = prompt("Type (receipt/issue/adjust):", "receipt") || "receipt";
              const quantity = parseFloat(prompt("Quantity:") || "0"); if (!quantity) return;
              await createMovement({ product_id: products[0].id, warehouse_id: warehouses[0].id, movement_type, quantity });
              rStock();
            }}>+ Movement</button>
          </div>
        </div>
        <table>
          <thead><tr><th>SKU</th><th>Name</th><th>Cost</th><th>Price</th><th>Reorder @</th></tr></thead>
          <tbody>
            {products.map((p: any) => (
              <tr key={p.id}>
                <td style={{ fontWeight: 600 }}>{p.sku}</td>
                <td>{p.name}</td>
                <td>${p.unit_cost}</td>
                <td>${p.unit_price}</td>
                <td>{p.reorder_point}</td>
              </tr>
            ))}
            {products.length === 0 && <tr><td colSpan={5} style={{ textAlign: "center", color: "var(--gray-500)", padding: "1rem" }}>No products.</td></tr>}
          </tbody>
        </table>
      </div>

      <div className="card" style={{ marginTop: "1rem" }}>
        <h3 style={{ marginBottom: "0.5rem" }}>Stock levels</h3>
        <table>
          <thead><tr><th>SKU</th><th>Name</th><th>Warehouse</th><th>Qty</th><th>Reorder?</th></tr></thead>
          <tbody>
            {stock.map((s: any, i: number) => (
              <tr key={i}>
                <td style={{ fontWeight: 600 }}>{s.sku}</td>
                <td>{s.name}</td>
                <td>{s.warehouse}</td>
                <td>{s.quantity}</td>
                <td>{s.below_reorder ? <span className="badge badge-red">Low</span> : <span className="badge badge-green">OK</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
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
