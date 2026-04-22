import { useEffect, useState } from "react";
import PageHeader from "../../shell/PageHeader";
import { Icon } from "../../shell/icons";
import { notifyUser, promptForValues, confirmAction } from "../../shell/modalService";
import { useAppSelector } from "../../app/hooks";

const API = (import.meta.env.VITE_API_URL as string) || "";

type ReturnRow = {
  id: string; invoice_id: string; rma_number: string;
  status: "requested" | "approved" | "received" | "refunded" | "rejected";
  refund_amount: number; reason: string | null;
  received_at: string | null; refunded_at: string | null; created_at: string;
};

const NEXT_STATES: Record<ReturnRow["status"], ReturnRow["status"][]> = {
  requested: ["approved", "rejected"],
  approved: ["received", "rejected"],
  received: ["refunded"],
  refunded: [],
  rejected: [],
};

function statusBadgeClass(s: ReturnRow["status"]): string {
  return {
    requested: "badge badge-yellow",
    approved: "badge badge-blue",
    received: "badge badge-blue",
    refunded: "badge badge-green",
    rejected: "badge badge-red",
  }[s];
}

/**
 * Returns / RMA admin. Lists all RMAs, allows status transitions through
 * the configured workflow (requested → approved → received → refunded),
 * and supports creating new returns against an existing invoice.
 */
export default function ReturnsPage() {
  const token = useAppSelector((s) => s.auth.token);
  const [rows, setRows] = useState<ReturnRow[]>([]);
  const auth = token ? { Authorization: `Bearer ${token}` } : undefined;

  const refresh = async () => {
    if (!token) return;
    const r = await fetch(`${API}/api/returns`, { headers: auth });
    if (r.ok) setRows(await r.json());
  };
  useEffect(() => { void refresh(); }, [token]); // eslint-disable-line react-hooks/exhaustive-deps

  const newReturn = async () => {
    const v = await promptForValues({
      title: "New RMA",
      description: "Creates a return authorization against an existing invoice.",
      fields: [
        { name: "invoice_id", label: "Invoice ID (UUID)", required: true },
        { name: "rma_number", label: "RMA number", required: true, placeholder: "e.g. RMA-2026-0001" },
        { name: "reason", label: "Reason", kind: "textarea" },
        { name: "description", label: "First line — description", placeholder: "What's being returned?" },
        { name: "quantity", label: "Quantity", defaultValue: "1", kind: "number" },
        { name: "unit_price", label: "Unit price", defaultValue: "0", kind: "number" },
      ],
    });
    if (!v) return;
    const lines = v.description
      ? [{ description: v.description, quantity: Number(v.quantity || 1), unit_price: Number(v.unit_price || 0) }]
      : [];
    const r = await fetch(`${API}/api/returns`, {
      method: "POST", headers: { ...auth, "Content-Type": "application/json" },
      body: JSON.stringify({
        invoice_id: v.invoice_id, rma_number: v.rma_number, reason: v.reason || null, lines,
      }),
    });
    if (!r.ok) { await notifyUser({ title: "Create failed", description: `HTTP ${r.status}` }); return; }
    await refresh();
  };

  const transition = async (row: ReturnRow, next: ReturnRow["status"]) => {
    const ok = next === "refunded"
      ? await confirmAction({
          title: `Refund RMA ${row.rma_number}?`,
          description: `Refund amount: $${row.refund_amount.toFixed(2)}. This records the refund timestamp but does not call a payment gateway.`,
          submitLabel: "Refund",
        })
      : true;
    if (!ok) return;
    const r = await fetch(`${API}/api/returns/${row.id}/status?new_status=${next}`, {
      method: "PATCH", headers: auth,
    });
    if (!r.ok) { await notifyUser({ title: "Update failed", description: `HTTP ${r.status}` }); return; }
    await refresh();
  };

  return (
    <div>
      <PageHeader
        title="Returns (RMA)"
        subtitle="Process return merchandise authorizations and refunds against invoiced orders."
        breadcrumbs={[{ to: "/finance", label: "Finance" }, { label: "Returns" }]}
        meta={
          <button className="btn btn-sm btn-primary" onClick={newReturn}>
            <Icon.Plus size={12} /> New RMA
          </button>
        }
      />

      <div className="card" style={{ padding: 0 }}>
        <table style={{ width: "100%" }}>
          <thead>
            <tr>
              <th>RMA #</th>
              <th>Invoice</th>
              <th>Status</th>
              <th>Refund</th>
              <th>Received</th>
              <th>Refunded</th>
              <th style={{ minWidth: 160 }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td style={{ fontFamily: "monospace", fontWeight: 500 }}>{r.rma_number}</td>
                <td style={{ fontFamily: "monospace", fontSize: "0.78rem" }}>{r.invoice_id.slice(0, 8)}…</td>
                <td><span className={statusBadgeClass(r.status)}>{r.status}</span></td>
                <td>${r.refund_amount.toFixed(2)}</td>
                <td style={{ fontSize: "0.82rem" }}>{r.received_at ? new Date(r.received_at).toLocaleDateString() : "—"}</td>
                <td style={{ fontSize: "0.82rem" }}>{r.refunded_at ? new Date(r.refunded_at).toLocaleDateString() : "—"}</td>
                <td>
                  <div style={{ display: "inline-flex", gap: "0.25rem" }}>
                    {NEXT_STATES[r.status].map((ns) => (
                      <button
                        key={ns} className={`btn btn-sm ${ns === "refunded" ? "btn-primary" : ""}`}
                        onClick={() => transition(r, ns)}
                      >
                        → {ns}
                      </button>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={7} style={{ textAlign: "center", padding: "1.5rem", color: "var(--gray-500)" }}>
                  No RMAs yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
