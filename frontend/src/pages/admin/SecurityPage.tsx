import { useState } from "react";
import { useAppDispatch, useAppSelector } from "../../app/hooks";
import {
  useTotpEnrollMutation,
  useTotpConfirmMutation,
  useTotpDisableMutation,
  useGetMyFieldMasksQuery,
} from "../../services/api";
import { patchUser } from "../../services/authSlice";
import PageHeader from "../../shell/PageHeader";
import { Icon } from "../../shell/icons";
import { notifyUser } from "../../shell/modalService";

export default function SecurityPage() {
  const user = useAppSelector((s) => s.auth.user);
  const dispatch = useAppDispatch();
  const [enroll, { data: enrollData, isLoading: enrolling }] = useTotpEnrollMutation();
  const [confirm, { isLoading: confirming }] = useTotpConfirmMutation();
  const [disable, { isLoading: disabling }] = useTotpDisableMutation();
  const { data: fieldMasks } = useGetMyFieldMasksQuery();
  const [code, setCode] = useState("");
  const [disableForm, setDisableForm] = useState({ password: "", code: "" });

  const isEnabled = !!user?.is_totp_enabled;

  return (
    <div>
      <PageHeader
        title="Security"
        subtitle="Manage two-factor authentication and review which sensitive fields are masked for your role."
        breadcrumbs={[{ to: "/admin", label: "Admin" }, { label: "Security" }]}
      />

      <div className="card">
        <div className="card-header">
          <h2>Two-factor authentication</h2>
          {isEnabled ? (
            <span className="badge badge-green" style={{ display: "inline-flex", alignItems: "center", gap: "0.3rem" }}>
              <Icon.ShieldCheck size={12} /> Enabled
            </span>
          ) : (
            <span className="badge badge-gray">Off</span>
          )}
        </div>
        {isEnabled ? (
          <>
            <p style={{ fontSize: "0.85rem", color: "var(--gray-600)" }}>
              Login requires a 6-digit code from your authenticator app. To turn off 2FA, enter your password and a current code.
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem", maxWidth: 480 }}>
              <div className="form-group">
                <label>Password</label>
                <input
                  type="password"
                  value={disableForm.password}
                  onChange={(e) => setDisableForm({ ...disableForm, password: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>Current code</label>
                <input
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  maxLength={6}
                  value={disableForm.code}
                  onChange={(e) => setDisableForm({ ...disableForm, code: e.target.value.replace(/\D/g, "") })}
                />
              </div>
            </div>
            <button
              className="btn btn-sm btn-danger"
              disabled={disabling || !disableForm.password || disableForm.code.length !== 6}
              onClick={async () => {
                const r: any = await disable(disableForm);
                if (r.error) {
                  await notifyUser({ title: "Disable failed", description: (r.error as any)?.data?.detail });
                } else {
                  dispatch(patchUser({ is_totp_enabled: false }));
                  setDisableForm({ password: "", code: "" });
                  await notifyUser({ title: "Two-factor disabled" });
                }
              }}
            >
              Disable 2FA
            </button>
          </>
        ) : (
          <>
            <p style={{ fontSize: "0.85rem", color: "var(--gray-600)" }}>
              Add a second factor to your account. You'll need an authenticator app like Google Authenticator, Authy, or 1Password.
            </p>
            {!enrollData ? (
              <button
                className="btn btn-sm btn-primary"
                disabled={enrolling}
                onClick={async () => {
                  const r: any = await enroll();
                  if (r.error) {
                    await notifyUser({ title: "Enrolment failed", description: (r.error as any)?.data?.detail });
                  }
                }}
              >
                <Icon.Totp size={14} /> Start enrolment
              </button>
            ) : (
              <div style={{ marginTop: "0.5rem" }}>
                <div style={{ marginBottom: "0.75rem", fontSize: "0.85rem", color: "var(--gray-700)" }}>
                  <strong>Step 1.</strong> Open your authenticator app and add a new account using either of these:
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem", marginBottom: "0.75rem", maxWidth: 540 }}>
                  <div>
                    <div style={{ fontSize: "0.75rem", color: "var(--gray-500)", marginBottom: "0.2rem" }}>Secret (manual entry)</div>
                    <code
                      style={{
                        display: "inline-block",
                        padding: "0.4rem 0.6rem",
                        background: "var(--gray-50)",
                        border: "1px solid var(--gray-200)",
                        borderRadius: "var(--radius-sm)",
                        fontSize: "0.85rem",
                        letterSpacing: "0.05em",
                      }}
                    >
                      {enrollData.secret}
                    </code>
                  </div>
                  <div>
                    <div style={{ fontSize: "0.75rem", color: "var(--gray-500)", marginBottom: "0.2rem" }}>Provisioning URI (paste into a QR-code generator if needed)</div>
                    <code
                      style={{
                        display: "inline-block",
                        padding: "0.4rem 0.6rem",
                        background: "var(--gray-50)",
                        border: "1px solid var(--gray-200)",
                        borderRadius: "var(--radius-sm)",
                        fontSize: "0.72rem",
                        wordBreak: "break-all",
                        maxWidth: "100%",
                      }}
                    >
                      {enrollData.provisioning_uri}
                    </code>
                  </div>
                </div>
                <div style={{ marginBottom: "0.75rem", fontSize: "0.85rem", color: "var(--gray-700)" }}>
                  <strong>Step 2.</strong> Enter the 6-digit code your app shows now:
                </div>
                <div style={{ display: "flex", gap: "0.5rem", alignItems: "flex-end" }}>
                  <div className="form-group" style={{ marginBottom: 0, flex: "0 0 auto" }}>
                    <input
                      type="text"
                      inputMode="numeric"
                      pattern="[0-9]*"
                      maxLength={6}
                      value={code}
                      onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                      style={{ width: 130, fontFamily: "monospace", fontSize: "1.1rem", letterSpacing: "0.2em", textAlign: "center" }}
                    />
                  </div>
                  <button
                    className="btn btn-sm btn-primary"
                    disabled={confirming || code.length !== 6}
                    onClick={async () => {
                      const r: any = await confirm({ code });
                      if (r.error) {
                        await notifyUser({ title: "Wrong code", description: (r.error as any)?.data?.detail });
                      } else {
                        dispatch(patchUser({ is_totp_enabled: true }));
                        setCode("");
                        await notifyUser({ title: "Two-factor enabled", description: "You'll be prompted for a code on next login." });
                      }
                    }}
                  >
                    Verify and enable
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      <div className="card">
        <div className="card-header">
          <h2>Field masks for your role</h2>
        </div>
        <p style={{ fontSize: "0.85rem", color: "var(--gray-600)" }}>
          These fields are hidden from API responses for your account. Admins can edit the rules under Access Control.
        </p>
        {!fieldMasks || Object.keys(fieldMasks).length === 0 ? (
          <div style={{ color: "var(--gray-500)", fontSize: "0.85rem" }}>
            No fields are currently masked for your role.
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Entity</th>
                <th>Hidden fields</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(fieldMasks).map(([entity, fields]) => (
                <tr key={entity}>
                  <td><code>{entity}</code></td>
                  <td>
                    {fields.map((f: string) => (
                      <span
                        key={f}
                        className="badge badge-gray"
                        style={{ marginRight: "0.3rem", display: "inline-flex", alignItems: "center", gap: "0.2rem" }}
                      >
                        <Icon.Lock size={10} /> {f}
                      </span>
                    ))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
