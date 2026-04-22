import { useEffect, useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useLoginMutation, useGetActiveSsoProvidersQuery } from "../services/api";
import { setCredentials } from "../services/authSlice";
import { useAppDispatch } from "../app/hooks";

export default function LoginPage() {
  const [login, { isLoading }] = useLoginMutation();
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as any)?.from?.pathname || "/";

  const [form, setForm] = useState({ email: "", password: "", totp_code: "" });
  const [error, setError] = useState("");
  const [needTotp, setNeedTotp] = useState(false);
  const { data: ssoProviders = [] } = useGetActiveSsoProvidersQuery();

  useEffect(() => {
    // Surface SSO error from query string (set by /api/sso/callback)
    const params = new URLSearchParams(location.search);
    const ssoErr = params.get("sso_error");
    if (ssoErr) setError(`SSO failed: ${ssoErr}`);
  }, [location.search]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      const payload = needTotp ? form : { email: form.email, password: form.password };
      const result = await login(payload as any).unwrap();
      dispatch(setCredentials({ token: result.access_token, user: result.user }));
      navigate(from, { replace: true });
    } catch (err: any) {
      const detail = err?.data?.detail || "Invalid email or password";
      if (detail === "TOTP_REQUIRED") {
        setNeedTotp(true);
        setError("");
      } else {
        setError(detail);
      }
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-header">
          <div style={{ width: 48, height: 48, borderRadius: 12, background: "var(--primary)", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 1rem", boxShadow: "0 4px 12px rgba(79,70,229,0.3)" }}>
            <span style={{ color: "white", fontWeight: 700, fontSize: "1.2rem" }}>PM</span>
          </div>
          <h1>Welcome back</h1>
          <p>Sign in to PMBOK Project Management</p>
        </div>
        <form onSubmit={handleSubmit}>
          {error && <div className="auth-error">{error}</div>}
          <div className="form-group">
            <label>Email address</label>
            <input
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              placeholder="you@example.com"
              required
              autoFocus
            />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              placeholder="Enter your password"
              required
            />
          </div>
          {needTotp && (
            <div className="form-group">
              <label>Authentication code</label>
              <input
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                maxLength={6}
                value={form.totp_code}
                onChange={(e) => setForm({ ...form, totp_code: e.target.value.replace(/\D/g, "") })}
                placeholder="6-digit code from your authenticator app"
                required
                autoFocus
              />
              <div style={{ fontSize: "0.72rem", color: "var(--gray-500)", marginTop: "0.3rem" }}>
                Open your authenticator app and enter the current code for this account.
              </div>
            </div>
          )}
          <button type="submit" className="btn btn-primary auth-btn" disabled={isLoading}>
            {isLoading ? "Signing in..." : needTotp ? "Verify code" : "Sign in"}
          </button>
        </form>
        {ssoProviders.length > 0 && (
          <div style={{ marginTop: "1rem" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", margin: "0.75rem 0", color: "var(--gray-400)", fontSize: "0.72rem" }}>
              <hr style={{ flex: 1, border: 0, borderTop: "1px solid var(--gray-200)" }} />
              <span>OR CONTINUE WITH</span>
              <hr style={{ flex: 1, border: 0, borderTop: "1px solid var(--gray-200)" }} />
            </div>
            {ssoProviders.map((p: any) => (
              <a
                key={p.id}
                href={`${import.meta.env.VITE_API_URL || ""}/api/sso/start?provider_id=${p.id}`}
                className="btn auth-btn"
                style={{ width: "100%", marginBottom: "0.4rem", display: "flex", justifyContent: "center" }}
              >
                Sign in with {p.name}
              </a>
            ))}
          </div>
        )}
        <p className="auth-footer" style={{ marginTop: "0.5rem" }}>
          <Link to="/forgot-password">Forgot your password?</Link>
        </p>
        <p className="auth-footer">
          Don't have an account? <Link to="/signup">Create one</Link>
        </p>
      </div>
    </div>
  );
}
