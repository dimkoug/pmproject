import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

const API = (import.meta.env.VITE_API_URL as string) || "";

export default function PortalLoginPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const t = params.get("t");
    if (!t) {
      setError("Missing token in link.");
      return;
    }
    (async () => {
      try {
        const r = await fetch(`${API}/api/portal/exchange`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token: t }),
        });
        if (!r.ok) {
          const body = await r.json().catch(() => ({}));
          throw new Error(body?.detail || `HTTP ${r.status}`);
        }
        const data = await r.json();
        sessionStorage.setItem("portal_token", data.access_token);
        sessionStorage.setItem("portal_company", JSON.stringify(data.company));
        navigate("/portal", { replace: true });
      } catch (e: any) {
        setError(e?.message || "Could not exchange token.");
      }
    })();
  }, [params, navigate]);

  return (
    <div className="auth-page">
      <div className="auth-card" style={{ textAlign: "center" }}>
        <h1>Customer portal</h1>
        {error ? (
          <>
            <p style={{ color: "var(--danger)", fontSize: "0.85rem", marginTop: "0.75rem" }}>{error}</p>
            <p style={{ color: "var(--gray-500)", fontSize: "0.78rem", marginTop: "0.5rem" }}>
              Magic links are single-use and expire. Ask your contact for a fresh one.
            </p>
          </>
        ) : (
          <p style={{ color: "var(--gray-500)", fontSize: "0.85rem" }}>Signing you in…</p>
        )}
      </div>
    </div>
  );
}
