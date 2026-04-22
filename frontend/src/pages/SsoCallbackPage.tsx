import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAppDispatch } from "../app/hooks";
import { setCredentials } from "../services/authSlice";

export default function SsoCallbackPage() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();

  useEffect(() => {
    // Token comes back as a URL fragment so it never hits server logs
    const fragment = window.location.hash.replace(/^#/, "");
    const params = new URLSearchParams(fragment);
    const token = params.get("token");
    const userId = params.get("user_id");

    if (!token) {
      navigate("/login?sso_error=missing_token", { replace: true });
      return;
    }

    // We have a token but not the full user payload — fetch /me before redirecting
    const apiUrl = (import.meta.env.VITE_API_URL as string) || "";
    fetch(`${apiUrl}/api/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((user) => {
        if (userId && user.id !== userId) {
          throw new Error("user_id mismatch");
        }
        dispatch(setCredentials({ token, user }));
        navigate("/", { replace: true });
      })
      .catch((e) => {
        navigate(`/login?sso_error=${encodeURIComponent(e.message || "unknown")}`, { replace: true });
      });
  }, [dispatch, navigate]);

  return (
    <div className="auth-page">
      <div className="auth-card" style={{ textAlign: "center" }}>
        <h1>Signing you in…</h1>
        <p style={{ color: "var(--gray-500)", fontSize: "0.85rem" }}>Completing single sign-on, one moment.</p>
      </div>
    </div>
  );
}
