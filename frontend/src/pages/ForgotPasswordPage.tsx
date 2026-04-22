import { useState } from "react";
import { Link } from "react-router-dom";

const API = (import.meta.env.VITE_API_URL as string) || "";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await fetch(`${API}/api/auth/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim() }),
      });
    } finally {
      setLoading(false);
      setDone(true);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-header">
          <h1>Forgot your password?</h1>
          <p>Enter the email you use to sign in and we'll send you a reset link.</p>
        </div>
        {done ? (
          <>
            <div style={{ padding: "1rem", background: "var(--success-light)", borderRadius: "var(--radius)", color: "var(--gray-700)", fontSize: "0.85rem" }}>
              If an account exists for <strong>{email}</strong>, we've sent a reset link there. The link is valid for 1 hour.
            </div>
            <p className="auth-footer" style={{ marginTop: "1rem" }}>
              <Link to="/login">Back to sign in</Link>
            </p>
          </>
        ) : (
          <>
            <form onSubmit={submit}>
              <div className="form-group">
                <label>Email address</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  required
                  autoFocus
                />
              </div>
              <button type="submit" className="btn btn-primary auth-btn" disabled={loading || !email.trim()}>
                {loading ? "Sending…" : "Send reset link"}
              </button>
            </form>
            <p className="auth-footer">
              <Link to="/login">Back to sign in</Link>
            </p>
          </>
        )}
      </div>
    </div>
  );
}
