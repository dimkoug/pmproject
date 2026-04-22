import { useEffect, useState } from "react";
import PageHeader from "../../shell/PageHeader";
import { Icon } from "../../shell/icons";
import { confirmAction, notifyUser } from "../../shell/modalService";
import { useAppSelector } from "../../app/hooks";

const API = (import.meta.env.VITE_API_URL as string) || "";

type TemplateRow = { id: string; key: string; subject: string; updated_at: string };
type TemplateFull = TemplateRow & { body_text: string; body_html: string | null };

/**
 * Admin surface for the `email_templates` DB-backed overrides. The backend
 * `render_template()` helper reads this table first and falls back to
 * hardcoded defaults — so deleting a row here is safe (it just reverts the
 * template to the built-in copy).
 */
export default function EmailTemplatesPage() {
  const token = useAppSelector((s) => s.auth.token);
  const [rows, setRows] = useState<TemplateRow[]>([]);
  const [selected, setSelected] = useState<TemplateFull | null>(null);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const authHeader = token ? { Authorization: `Bearer ${token}` } : undefined;

  const refresh = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/admin/email-templates`, { headers: authHeader });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setRows(await r.json());
    } catch (e: any) {
      await notifyUser({ title: "Load failed", description: e?.message });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void refresh(); }, [token]); // eslint-disable-line react-hooks/exhaustive-deps

  const open = async (key: string) => {
    const r = await fetch(`${API}/api/admin/email-templates/${encodeURIComponent(key)}`, { headers: authHeader });
    if (!r.ok) { await notifyUser({ title: "Fetch failed", description: `HTTP ${r.status}` }); return; }
    setSelected(await r.json());
  };

  const save = async () => {
    if (!selected) return;
    const r = await fetch(`${API}/api/admin/email-templates/${selected.id}`, {
      method: "PATCH",
      headers: { ...authHeader, "Content-Type": "application/json" },
      body: JSON.stringify({
        key: selected.key,
        subject: selected.subject,
        body_text: selected.body_text,
        body_html: selected.body_html || null,
      }),
    });
    if (!r.ok) { await notifyUser({ title: "Save failed", description: `HTTP ${r.status}` }); return; }
    await notifyUser({ title: "Saved", description: selected.key });
    setSelected(null);
    await refresh();
  };

  const remove = async () => {
    if (!selected) return;
    const ok = await confirmAction({
      title: `Delete template "${selected.key}"?`,
      description: "The backend will fall back to the hardcoded default for this template.",
      submitLabel: "Delete",
      dangerous: true,
    });
    if (!ok) return;
    const r = await fetch(`${API}/api/admin/email-templates/${selected.id}`, {
      method: "DELETE", headers: authHeader,
    });
    if (r.status !== 204) { await notifyUser({ title: "Delete failed", description: `HTTP ${r.status}` }); return; }
    setSelected(null);
    await refresh();
  };

  const create = async (form: TemplateFull) => {
    const r = await fetch(`${API}/api/admin/email-templates`, {
      method: "POST",
      headers: { ...authHeader, "Content-Type": "application/json" },
      body: JSON.stringify({
        key: form.key, subject: form.subject,
        body_text: form.body_text, body_html: form.body_html || null,
      }),
    });
    if (!r.ok) { await notifyUser({ title: "Create failed", description: `HTTP ${r.status}` }); return; }
    setCreating(false);
    await refresh();
  };

  return (
    <div>
      <PageHeader
        title="Email templates"
        subtitle="Override the default copy used in password reset / approval / expiry / mention emails. Placeholders are wrapped in {curly_braces}."
        breadcrumbs={[{ to: "/admin", label: "Admin" }, { label: "Email templates" }]}
        meta={
          <button className="btn btn-sm btn-primary" onClick={() => setCreating(true)}>
            <Icon.Plus size={12} /> New template
          </button>
        }
      />

      <div className="card" style={{ padding: 0 }}>
        <table style={{ width: "100%" }}>
          <thead>
            <tr>
              <th>Key</th>
              <th>Subject</th>
              <th>Last updated</th>
              <th style={{ width: 100 }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td style={{ fontFamily: "monospace" }}>{r.key}</td>
                <td>{r.subject}</td>
                <td style={{ fontSize: "0.82rem", color: "var(--gray-500)" }}>
                  {r.updated_at ? new Date(r.updated_at).toLocaleString() : "—"}
                </td>
                <td>
                  <button className="btn btn-sm" onClick={() => open(r.key)}>Edit</button>
                </td>
              </tr>
            ))}
            {!loading && rows.length === 0 && (
              <tr>
                <td colSpan={4} style={{ textAlign: "center", padding: "1.5rem", color: "var(--gray-500)" }}>
                  No overrides. All templates use the built-in defaults.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {(selected || creating) && (
        <div className="modal-overlay" onClick={() => { setSelected(null); setCreating(false); }}>
          <div className="modal" style={{ maxWidth: 720 }} onClick={(e) => e.stopPropagation()}>
            <TemplateForm
              initial={selected ?? { id: "", key: "", subject: "", body_text: "", body_html: "", updated_at: "" }}
              isNew={creating}
              onSave={creating ? (v) => create(v) : (v) => { setSelected(v); void save(); }}
              onChange={(v) => { if (!creating) setSelected(v); }}
              onCancel={() => { setSelected(null); setCreating(false); }}
              onDelete={creating ? undefined : remove}
            />
          </div>
        </div>
      )}
    </div>
  );
}


function TemplateForm({ initial, isNew, onSave, onChange, onCancel, onDelete }: {
  initial: TemplateFull;
  isNew: boolean;
  onSave: (v: TemplateFull) => void | Promise<void>;
  onChange?: (v: TemplateFull) => void;
  onCancel: () => void;
  onDelete?: () => void | Promise<void>;
}) {
  const [form, setForm] = useState<TemplateFull>(initial);
  const patch = (p: Partial<TemplateFull>) => {
    const next = { ...form, ...p };
    setForm(next);
    onChange?.(next);
  };

  return (
    <div>
      <h3 style={{ marginTop: 0 }}>{isNew ? "New template" : `Edit "${form.key}"`}</h3>
      <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
        <label>
          <div style={{ fontSize: "0.78rem", color: "var(--gray-500)" }}>Key</div>
          <input
            type="text" value={form.key}
            onChange={(e) => patch({ key: e.target.value })}
            disabled={!isNew}
            style={{ width: "100%", fontFamily: "monospace" }}
          />
        </label>
        <label>
          <div style={{ fontSize: "0.78rem", color: "var(--gray-500)" }}>Subject</div>
          <input
            type="text" value={form.subject}
            onChange={(e) => patch({ subject: e.target.value })}
            style={{ width: "100%" }}
          />
        </label>
        <label>
          <div style={{ fontSize: "0.78rem", color: "var(--gray-500)" }}>Plain-text body</div>
          <textarea
            value={form.body_text}
            onChange={(e) => patch({ body_text: e.target.value })}
            rows={6}
            style={{ width: "100%", fontFamily: "monospace", fontSize: "0.85rem" }}
          />
        </label>
        <label>
          <div style={{ fontSize: "0.78rem", color: "var(--gray-500)" }}>HTML body (optional)</div>
          <textarea
            value={form.body_html || ""}
            onChange={(e) => patch({ body_html: e.target.value })}
            rows={8}
            style={{ width: "100%", fontFamily: "monospace", fontSize: "0.85rem" }}
          />
        </label>
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", marginTop: "1rem" }}>
        {onDelete ? (
          <button className="btn btn-sm btn-danger" onClick={() => void onDelete()}>Delete</button>
        ) : <span />}
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button className="btn btn-sm" onClick={onCancel}>Cancel</button>
          <button className="btn btn-sm btn-primary" onClick={() => onSave(form)}>Save</button>
        </div>
      </div>
    </div>
  );
}
