import { useEffect, useRef, useState } from "react";
import { useAppSelector } from "../../app/hooks";
import { Icon } from "../../shell/icons";
import { notifyUser } from "../../shell/modalService";

const API = (import.meta.env.VITE_API_URL as string) || "";

type Product = { id: string; sku: string; name: string; barcode: string | null; unit_price: number; unit_cost: number };
type Warehouse = { id: string; code: string; name: string };

/**
 * Barcode lookup + FIFO issue side-panel. Scanner-friendly: the input
 * autofocuses and submits on Enter, matching how USB scanners emit
 * keystrokes. FIFO issue hits /api/erp/stock/fifo-issue which drains the
 * oldest batches first and returns a per-batch cost breakdown.
 */
export default function BarcodeFifoPanel({ warehouses }: { warehouses: Warehouse[] }) {
  const token = useAppSelector((s) => s.auth.token);
  const [code, setCode] = useState("");
  const [product, setProduct] = useState<Product | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [warehouseId, setWarehouseId] = useState<string>(warehouses[0]?.id || "");
  const [quantity, setQuantity] = useState("1");
  const [result, setResult] = useState<any>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const auth = token ? { Authorization: `Bearer ${token}` } : undefined;

  useEffect(() => { inputRef.current?.focus(); }, []);
  useEffect(() => { if (!warehouseId && warehouses.length) setWarehouseId(warehouses[0].id); }, [warehouses, warehouseId]);

  const lookup = async (raw: string) => {
    setErr(null);
    setProduct(null);
    setResult(null);
    if (!raw.trim()) return;
    const r = await fetch(`${API}/api/erp/products/by-barcode/${encodeURIComponent(raw.trim())}`, { headers: auth });
    if (r.status === 404) { setErr("Unknown barcode"); return; }
    if (!r.ok) { setErr(`Lookup failed: HTTP ${r.status}`); return; }
    setProduct(await r.json());
  };

  const issue = async () => {
    if (!product || !warehouseId) return;
    const qty = Number(quantity);
    if (!qty || qty <= 0) { setErr("Quantity must be positive"); return; }
    const r = await fetch(`${API}/api/erp/stock/fifo-issue`, {
      method: "POST",
      headers: { ...auth, "Content-Type": "application/json" },
      body: JSON.stringify({ product_id: product.id, warehouse_id: warehouseId, quantity: qty }),
    });
    if (!r.ok) {
      const body = await r.json().catch(() => ({}));
      setErr(body.detail || `Issue failed: HTTP ${r.status}`);
      return;
    }
    setResult(await r.json());
    await notifyUser({ title: "Stock issued", description: `${qty} × ${product.sku} drained FIFO` });
    // Auto-reset for the next scan
    setCode("");
    setProduct(null);
    setQuantity("1");
    inputRef.current?.focus();
  };

  return (
    <div className="card" style={{ marginBottom: "1rem" }}>
      <div className="card-header">
        <h3>Scan & issue (FIFO)</h3>
        <span style={{ fontSize: "0.78rem", color: "var(--gray-500)" }}>
          Scan a barcode, confirm the product, then issue from oldest batches first.
        </span>
      </div>

      <form
        onSubmit={(e) => { e.preventDefault(); void lookup(code); }}
        style={{ display: "flex", gap: "0.5rem", alignItems: "center", marginBottom: "0.75rem" }}
      >
        <Icon.Search size={14} />
        <input
          ref={inputRef}
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="Scan or type a barcode…"
          style={{ flex: 1, padding: "0.5rem", fontFamily: "monospace" }}
          autoFocus
        />
        <button type="submit" className="btn btn-sm">Look up</button>
      </form>

      {err && <div style={{ color: "var(--danger)", fontSize: "0.85rem", marginBottom: "0.5rem" }}>{err}</div>}

      {product && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr auto", gap: "0.75rem", alignItems: "end" }}>
          <div>
            <div style={{ fontSize: "0.78rem", color: "var(--gray-500)" }}>Product</div>
            <div style={{ fontWeight: 500 }}>{product.name}</div>
            <div style={{ fontFamily: "monospace", fontSize: "0.78rem" }}>{product.sku}</div>
          </div>
          <label>
            <div style={{ fontSize: "0.78rem", color: "var(--gray-500)" }}>Warehouse</div>
            <select
              value={warehouseId}
              onChange={(e) => setWarehouseId(e.target.value)}
              style={{ width: "100%", padding: "0.45rem" }}
            >
              {warehouses.map((w) => <option key={w.id} value={w.id}>{w.code} — {w.name}</option>)}
            </select>
          </label>
          <label>
            <div style={{ fontSize: "0.78rem", color: "var(--gray-500)" }}>Quantity</div>
            <input
              type="number" step="0.01" min="0"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              style={{ width: "100%", padding: "0.45rem" }}
            />
          </label>
          <button className="btn btn-primary" onClick={issue}>
            Issue FIFO
          </button>
        </div>
      )}

      {result && (
        <div style={{ marginTop: "0.75rem", padding: "0.6rem 0.75rem", background: "var(--gray-50)", borderRadius: "var(--radius-sm)" }}>
          <div style={{ fontSize: "0.82rem", marginBottom: "0.35rem" }}>
            Consumed from {result.consumed.length} batch{result.consumed.length === 1 ? "" : "es"} · total cost ${result.total_cost?.toFixed(2)}
          </div>
          <table style={{ width: "100%", fontSize: "0.78rem" }}>
            <thead><tr><th style={{ textAlign: "left" }}>Batch</th><th>Qty taken</th><th>Unit cost</th><th>Remaining</th></tr></thead>
            <tbody>
              {result.consumed.map((c: any) => (
                <tr key={c.batch_id}>
                  <td style={{ fontFamily: "monospace" }}>{c.batch_code}</td>
                  <td>{c.qty_taken}</td>
                  <td>${(c.unit_cost || 0).toFixed(2)}</td>
                  <td>{c.remaining_in_batch}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
