import { useCallback, useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useFormat } from "../../i18n/format";

const API = (import.meta.env.VITE_API_URL as string) || "";

type Invoice = {
  id: string;
  invoice_number: string;
  status: string;
  issue_date?: string | null;
  due_date?: string | null;
  total: number;
  paid_amount: number;
  outstanding: number;
  currency: string;
};

type Company = { id: string; name: string };

export default function PortalDashboardPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [company, setCompany] = useState<Company | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { formatDate, formatCurrency } = useFormat();

  const token = sessionStorage.getItem("portal_token");
  const cached = sessionStorage.getItem("portal_company");

  const load = useCallback(async () => {
    if (!token) {
      navigate("/portal/login", { replace: true });
      return;
    }
    setLoading(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [meR, invR] = await Promise.all([
        fetch(`${API}/api/portal/me`, { headers }),
        fetch(`${API}/api/portal/invoices`, { headers }),
      ]);
      if (meR.status === 401 || invR.status === 401) {
        sessionStorage.removeItem("portal_token");
        sessionStorage.removeItem("portal_company");
        navigate("/portal/login", { replace: true });
        return;
      }
      setCompany(await meR.json());
      setInvoices(await invR.json());
    } catch (e: any) {
      setError(e?.message || "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [token, navigate]);

  useEffect(() => {
    if (cached) {
      try {
        setCompany(JSON.parse(cached));
      } catch {
        // ignore
      }
    }
    void load();
  }, [load, cached]);

  const pay = async (invoiceId: string) => {
    if (!token) return;
    try {
      const r = await fetch(`${API}/api/portal/invoices/${invoiceId}/checkout`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) {
        const body = await r.json().catch(() => ({}));
        alert(body?.detail || `Payment setup failed (HTTP ${r.status})`);
        return;
      }
      const data = await r.json();
      if (data.url) window.location.href = data.url;
    } catch (e: any) {
      alert(`Payment failed: ${e?.message || e}`);
    }
  };

  const signOut = () => {
    sessionStorage.removeItem("portal_token");
    sessionStorage.removeItem("portal_company");
    navigate("/portal/login");
  };

  const justPaidId = params.get("paid");
  const justCancelledId = params.get("cancelled");

  return (
    <div style={{ minHeight: "100vh", background: "var(--gray-50)", padding: "2rem 1rem" }}>
      <div style={{ maxWidth: 920, margin: "0 auto" }}>
        <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
          <div>
            <div style={{ fontSize: "0.78rem", color: "var(--gray-500)" }}>Customer portal</div>
            <h1 style={{ fontSize: "1.4rem", fontWeight: 700, color: "var(--gray-900)", marginTop: "0.2rem" }}>
              {company?.name || "Welcome"}
            </h1>
          </div>
          <button className="btn btn-sm" onClick={signOut}>Sign out</button>
        </header>

        {justPaidId && (
          <div className="card" style={{ borderLeft: "3px solid var(--success)" }}>
            <strong style={{ color: "var(--success)" }}>Thank you — payment complete.</strong>
            <div style={{ fontSize: "0.82rem", color: "var(--gray-600)", marginTop: "0.3rem" }}>
              The invoice will reflect as paid here in a moment.
            </div>
          </div>
        )}
        {justCancelledId && (
          <div className="card" style={{ borderLeft: "3px solid var(--warning)" }}>
            Payment was cancelled — the invoice is still outstanding.
          </div>
        )}

        <div className="card" style={{ padding: 0 }}>
          <div style={{ padding: "0.75rem 1rem", borderBottom: "1px solid var(--gray-100)" }}>
            <strong>Your invoices</strong>
          </div>
          {loading ? (
            <div style={{ padding: "1rem", color: "var(--gray-500)" }}>Loading…</div>
          ) : error ? (
            <div style={{ padding: "1rem", color: "var(--danger)" }}>{error}</div>
          ) : invoices.length === 0 ? (
            <div style={{ padding: "2rem", color: "var(--gray-500)", textAlign: "center" }}>
              No invoices yet. We'll let your contact know if anything comes due.
            </div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Invoice</th>
                  <th>Issued</th>
                  <th>Due</th>
                  <th style={{ textAlign: "right" }}>Total</th>
                  <th style={{ textAlign: "right" }}>Outstanding</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {invoices.map((inv) => (
                  <tr key={inv.id}>
                    <td style={{ fontWeight: 500 }}>{inv.invoice_number}</td>
                    <td>{formatDate(inv.issue_date)}</td>
                    <td>{formatDate(inv.due_date)}</td>
                    <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{formatCurrency(inv.total, inv.currency || "USD")}</td>
                    <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums", fontWeight: 600 }}>
                      {formatCurrency(inv.outstanding, inv.currency || "USD")}
                    </td>
                    <td>
                      <span className={`badge ${inv.status === "paid" ? "badge-green" : inv.status === "overdue" ? "badge-red" : "badge-blue"}`}>
                        {inv.status}
                      </span>
                    </td>
                    <td>
                      {inv.outstanding > 0 && (
                        <button className="btn btn-sm btn-primary" onClick={() => pay(inv.id)}>Pay now</button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <p style={{ marginTop: "1rem", fontSize: "0.72rem", color: "var(--gray-500)", textAlign: "center" }}>
          Need help? Reply to your sales contact's last email — they'll get back to you the same way.
        </p>
      </div>
    </div>
  );
}
