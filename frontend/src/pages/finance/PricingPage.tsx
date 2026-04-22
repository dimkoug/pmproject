import { useEffect, useState } from "react";
import PageHeader from "../../shell/PageHeader";
import { Icon } from "../../shell/icons";
import { notifyUser, promptForValues } from "../../shell/modalService";
import { useAppSelector } from "../../app/hooks";

const API = (import.meta.env.VITE_API_URL as string) || "";

type PriceList = { id: string; name: string; currency: string; is_active: boolean };
type PriceListItem = { id: string; product_id: string; unit_price: number; min_quantity: number };
type Discount = {
  id: string; name: string; code: string | null;
  discount_type: "percent" | "amount"; value: number; min_subtotal: number;
  is_active: boolean; redemptions: number; max_redemptions: number | null;
  starts_at: string | null; ends_at: string | null;
};

/**
 * Pricing admin: manage named price lists + their tier items, and coupon
 * / auto-apply discount rules. The backend at /api/pricing/* drives the
 * same rules that /api/pricing/quote consumes during checkout.
 */
export default function PricingPage() {
  const token = useAppSelector((s) => s.auth.token);
  const [tab, setTab] = useState<"lists" | "discounts">("lists");
  const [lists, setLists] = useState<PriceList[]>([]);
  const [selectedList, setSelectedList] = useState<PriceList | null>(null);
  const [items, setItems] = useState<PriceListItem[]>([]);
  const [discounts, setDiscounts] = useState<Discount[]>([]);
  const auth = token ? { Authorization: `Bearer ${token}` } : undefined;

  const loadLists = async () => {
    const r = await fetch(`${API}/api/pricing/lists`, { headers: auth });
    if (r.ok) setLists(await r.json());
  };
  const loadItems = async (listId: string) => {
    const r = await fetch(`${API}/api/pricing/lists/${listId}/items`, { headers: auth });
    if (r.ok) setItems(await r.json());
  };
  const loadDiscounts = async () => {
    const r = await fetch(`${API}/api/pricing/discounts`, { headers: auth });
    if (r.ok) setDiscounts(await r.json());
  };

  useEffect(() => {
    if (!token) return;
    if (tab === "lists") void loadLists();
    else void loadDiscounts();
  }, [token, tab]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (selectedList) void loadItems(selectedList.id);
    else setItems([]);
  }, [selectedList]); // eslint-disable-line react-hooks/exhaustive-deps

  const createList = async () => {
    const v = await promptForValues({
      title: "New price list",
      fields: [
        { name: "name", label: "Name", required: true },
        { name: "currency", label: "Currency", defaultValue: "USD" },
      ],
    });
    if (!v) return;
    const r = await fetch(`${API}/api/pricing/lists`, {
      method: "POST", headers: { ...auth, "Content-Type": "application/json" },
      body: JSON.stringify({ name: v.name, currency: v.currency || "USD" }),
    });
    if (!r.ok) { await notifyUser({ title: "Create failed", description: `HTTP ${r.status}` }); return; }
    await loadLists();
  };

  const addItem = async () => {
    if (!selectedList) return;
    const v = await promptForValues({
      title: `Add tier to "${selectedList.name}"`,
      fields: [
        { name: "product_id", label: "Product ID (UUID)", required: true },
        { name: "unit_price", label: "Unit price", required: true, kind: "number" },
        { name: "min_quantity", label: "Applies from quantity", defaultValue: "1", kind: "number" },
      ],
    });
    if (!v) return;
    const r = await fetch(`${API}/api/pricing/lists/${selectedList.id}/items`, {
      method: "POST", headers: { ...auth, "Content-Type": "application/json" },
      body: JSON.stringify({
        product_id: v.product_id,
        unit_price: Number(v.unit_price),
        min_quantity: Number(v.min_quantity || 1),
      }),
    });
    if (!r.ok) { await notifyUser({ title: "Add failed", description: `HTTP ${r.status}` }); return; }
    await loadItems(selectedList.id);
  };

  const createDiscount = async () => {
    const v = await promptForValues({
      title: "New discount rule",
      fields: [
        { name: "name", label: "Name", required: true },
        { name: "code", label: "Coupon code (blank = auto-apply)" },
        { name: "discount_type", label: "Type", kind: "select", defaultValue: "percent",
          options: [{ value: "percent", label: "Percent (%)" }, { value: "amount", label: "Fixed amount" }]},
        { name: "value", label: "Value", required: true, kind: "number" },
        { name: "min_subtotal", label: "Minimum subtotal", defaultValue: "0", kind: "number" },
        { name: "max_redemptions", label: "Max redemptions (blank = unlimited)" },
      ],
    });
    if (!v) return;
    const r = await fetch(`${API}/api/pricing/discounts`, {
      method: "POST", headers: { ...auth, "Content-Type": "application/json" },
      body: JSON.stringify({
        name: v.name,
        code: v.code || null,
        discount_type: v.discount_type,
        value: Number(v.value),
        min_subtotal: Number(v.min_subtotal || 0),
        max_redemptions: v.max_redemptions ? Number(v.max_redemptions) : null,
      }),
    });
    if (!r.ok) { await notifyUser({ title: "Create failed", description: `HTTP ${r.status}` }); return; }
    await loadDiscounts();
  };

  return (
    <div>
      <PageHeader
        title="Pricing"
        subtitle="Price lists for tiered wholesale/retail pricing, plus coupon and auto-apply discount rules."
        breadcrumbs={[{ to: "/finance", label: "Finance" }, { label: "Pricing" }]}
      />

      <div style={{ display: "inline-flex", gap: "0.35rem", marginBottom: "1rem" }}>
        <button className={`btn btn-sm ${tab === "lists" ? "btn-primary" : ""}`} onClick={() => setTab("lists")}>Price lists</button>
        <button className={`btn btn-sm ${tab === "discounts" ? "btn-primary" : ""}`} onClick={() => setTab("discounts")}>Discounts & coupons</button>
      </div>

      {tab === "lists" && (
        <div style={{ display: "grid", gridTemplateColumns: "280px 1fr", gap: "1rem" }}>
          <div className="card">
            <div className="card-header">
              <h3>Price lists</h3>
              <button className="btn btn-sm btn-primary" onClick={createList}><Icon.Plus size={12} /> New</button>
            </div>
            <div>
              {lists.map((l) => (
                <div key={l.id}
                  onClick={() => setSelectedList(l)}
                  style={{
                    padding: "0.5rem 0.75rem", cursor: "pointer",
                    background: selectedList?.id === l.id ? "var(--primary-50, #eef2ff)" : undefined,
                    borderBottom: "1px solid var(--gray-100)",
                  }}>
                  <div style={{ fontWeight: 500 }}>{l.name}</div>
                  <div style={{ fontSize: "0.78rem", color: "var(--gray-500)" }}>
                    {l.currency} · {l.is_active ? "active" : "inactive"}
                  </div>
                </div>
              ))}
              {lists.length === 0 && (
                <div style={{ padding: "1rem", color: "var(--gray-500)", fontSize: "0.85rem" }}>
                  No price lists yet.
                </div>
              )}
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <h3>{selectedList ? `Tiers — ${selectedList.name}` : "Select a price list"}</h3>
              {selectedList && (
                <button className="btn btn-sm btn-primary" onClick={addItem}>
                  <Icon.Plus size={12} /> Add tier
                </button>
              )}
            </div>
            {selectedList ? (
              <table>
                <thead><tr><th>Product</th><th>Min qty</th><th>Unit price</th></tr></thead>
                <tbody>
                  {items.map((it) => (
                    <tr key={it.id}>
                      <td style={{ fontFamily: "monospace", fontSize: "0.78rem" }}>{it.product_id.slice(0, 8)}…</td>
                      <td>{it.min_quantity}</td>
                      <td>{it.unit_price.toFixed(2)} {selectedList.currency}</td>
                    </tr>
                  ))}
                  {items.length === 0 && (
                    <tr><td colSpan={3} style={{ textAlign: "center", padding: "1rem", color: "var(--gray-500)" }}>
                      No tiers yet.
                    </td></tr>
                  )}
                </tbody>
              </table>
            ) : null}
          </div>
        </div>
      )}

      {tab === "discounts" && (
        <div className="card">
          <div className="card-header">
            <h3>Discount rules</h3>
            <button className="btn btn-sm btn-primary" onClick={createDiscount}>
              <Icon.Plus size={12} /> New rule
            </button>
          </div>
          <table>
            <thead>
              <tr>
                <th>Name</th><th>Code</th><th>Type</th><th>Value</th>
                <th>Min subtotal</th><th>Redemptions</th><th>Active</th>
              </tr>
            </thead>
            <tbody>
              {discounts.map((d) => (
                <tr key={d.id}>
                  <td style={{ fontWeight: 500 }}>{d.name}</td>
                  <td style={{ fontFamily: "monospace" }}>{d.code || <span style={{ color: "var(--gray-500)" }}>auto-apply</span>}</td>
                  <td><span className="badge badge-blue">{d.discount_type}</span></td>
                  <td>{d.discount_type === "percent" ? `${d.value}%` : `$${d.value}`}</td>
                  <td>${d.min_subtotal}</td>
                  <td>{d.redemptions}{d.max_redemptions != null ? ` / ${d.max_redemptions}` : ""}</td>
                  <td>{d.is_active ? <span className="badge badge-green">Yes</span> : <span className="badge badge-gray">No</span>}</td>
                </tr>
              ))}
              {discounts.length === 0 && (
                <tr><td colSpan={7} style={{ textAlign: "center", padding: "1.5rem", color: "var(--gray-500)" }}>
                  No discount rules configured.
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
