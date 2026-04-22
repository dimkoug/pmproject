import { useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import {
  useGetAutomationCatalogQuery,
  useGetAutomationRulesQuery,
  useCreateAutomationRuleMutation,
  useUpdateAutomationRuleMutation,
  useDeleteAutomationRuleMutation,
  useGetAutomationRunsQuery,
  useGetTagsQuery,
} from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import DataTable from "../../shell/DataTable";
import { Icon } from "../../shell/icons";
import { useFormat } from "../../i18n/format";
import { confirmAction, notifyUser } from "../../shell/modalService";

type Rule = {
  id: string;
  name: string;
  description?: string | null;
  trigger_event: string;
  conditions: any[];
  actions: any[];
  is_active: boolean;
  created_at?: string | null;
};

type Catalog = {
  events: { value: string; label: string }[];
  ops: string[];
  actions: { value: string; label: string }[];
};

const STATUS_COLORS: Record<string, string> = {
  success: "badge-green",
  partial: "badge-yellow",
  failed: "badge-red",
  skipped: "badge-gray",
};

export default function AutomationPage() {
  const { data: catalog } = useGetAutomationCatalogQuery();
  const { data: rules = [], isLoading } = useGetAutomationRulesQuery();
  const { data: runs = [] } = useGetAutomationRunsQuery();
  const [createRule] = useCreateAutomationRuleMutation();
  const [updateRule] = useUpdateAutomationRuleMutation();
  const [deleteRule] = useDeleteAutomationRuleMutation();
  const { formatDateTime } = useFormat();

  const [editing, setEditing] = useState<Partial<Rule> | null>(null);

  const columns = useMemo<ColumnDef<Rule, any>[]>(
    () => [
      {
        accessorKey: "name",
        header: "Name",
        cell: (c) => (
          <div>
            <div style={{ fontWeight: 500 }}>{c.row.original.name}</div>
            {c.row.original.description && (
              <div style={{ fontSize: "0.72rem", color: "var(--gray-500)" }}>{c.row.original.description}</div>
            )}
          </div>
        ),
      },
      {
        accessorKey: "trigger_event",
        header: "Trigger",
        cell: (c) => <code style={{ fontSize: "0.78rem" }}>{c.getValue() as string}</code>,
      },
      {
        accessorKey: "conditions",
        header: "Conditions",
        cell: (c) => {
          const v = (c.getValue() as any[]) || [];
          return v.length === 0 ? "always" : `${v.length} clause${v.length === 1 ? "" : "s"}`;
        },
      },
      {
        accessorKey: "actions",
        header: "Actions",
        cell: (c) => {
          const v = (c.getValue() as any[]) || [];
          return v.map((a) => a.type).join(", ");
        },
      },
      {
        accessorKey: "is_active",
        header: "Active",
        cell: (c) =>
          c.getValue() ? (
            <span className="badge badge-green">on</span>
          ) : (
            <span className="badge badge-gray">off</span>
          ),
      },
      {
        id: "actions-col",
        header: "Actions",
        enableSorting: false,
        cell: (c) => {
          const row = c.row.original;
          return (
            <div style={{ display: "inline-flex", gap: "0.25rem" }} onClick={(e) => e.stopPropagation()}>
              <button
                className="btn btn-sm"
                onClick={() => setEditing({ ...row })}
              >
                Edit
              </button>
              <button
                className="btn btn-sm"
                onClick={async () => {
                  await updateRule({ id: row.id, body: { is_active: !row.is_active } });
                }}
              >
                {row.is_active ? "Disable" : "Enable"}
              </button>
              <button
                className="btn btn-sm btn-danger"
                onClick={async () => {
                  const ok = await confirmAction({
                    title: `Delete rule "${row.name}"?`,
                    submitLabel: "Delete",
                    dangerous: true,
                  });
                  if (!ok) return;
                  await deleteRule(row.id);
                }}
              >
                Delete
              </button>
            </div>
          );
        },
      },
    ],
    [updateRule, deleteRule],
  );

  return (
    <div>
      <PageHeader
        title="Automation rules"
        subtitle="When-this-then-that. Rules evaluate against audit events; condition matches trigger ordered actions."
        breadcrumbs={[{ to: "/admin", label: "Admin" }, { label: "Automation" }]}
      />
      <CommandBar
        items={[
          {
            key: "new",
            label: "New rule",
            variant: "primary",
            onClick: () => {
              if (!catalog) {
                void notifyUser({ title: "Loading catalog…", description: "Try again in a moment." });
                return;
              }
              setEditing({
                name: "",
                description: "",
                trigger_event: catalog.events[0]?.value,
                conditions: [],
                actions: [{ type: "log", params: { message: "Triggered: {entity_type}.{action}" } }],
                is_active: true,
              });
            },
          },
        ]}
      />
      <DataTable
        columns={columns}
        data={rules as Rule[]}
        isLoading={isLoading}
        emptyTitle="No automation rules"
        emptyDescription="Create your first rule — for example, post a webhook every time an invoice is created."
      />

      <h2 style={{ fontSize: "1.1rem", fontWeight: 700, margin: "1.5rem 0 0.5rem" }}>Recent runs</h2>
      <div className="card" style={{ padding: 0 }}>
        {(runs as any[]).length === 0 ? (
          <div style={{ padding: "1rem", color: "var(--gray-500)", fontSize: "0.82rem" }}>
            No runs yet — rules log a row here every time they evaluate.
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>When</th>
                <th>Event</th>
                <th>Actions</th>
                <th>Status</th>
                <th>Error</th>
              </tr>
            </thead>
            <tbody>
              {(runs as any[]).slice(0, 50).map((r) => (
                <tr key={r.id}>
                  <td style={{ fontSize: "0.78rem" }}>{formatDateTime(r.triggered_at)}</td>
                  <td><code style={{ fontSize: "0.78rem" }}>{r.event}</code></td>
                  <td style={{ fontSize: "0.78rem" }}>
                    {r.actions_run} ran
                    {r.actions_failed > 0 && <span style={{ color: "var(--danger)" }}> · {r.actions_failed} failed</span>}
                  </td>
                  <td>
                    <span className={`badge ${STATUS_COLORS[r.status] || "badge-gray"}`}>{r.status}</span>
                  </td>
                  <td style={{ fontSize: "0.72rem", color: "var(--gray-500)", maxWidth: 320 }}>{r.error || ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {editing && catalog && (
        <RuleEditor
          rule={editing}
          catalog={catalog as Catalog}
          onClose={() => setEditing(null)}
          onSave={async (rule) => {
            if (rule.id) {
              await updateRule({ id: rule.id, body: rule });
            } else {
              await createRule(rule);
            }
            setEditing(null);
          }}
        />
      )}
    </div>
  );
}

function RuleEditor({
  rule,
  catalog,
  onClose,
  onSave,
}: {
  rule: Partial<Rule>;
  catalog: Catalog;
  onClose: () => void;
  onSave: (rule: any) => Promise<void>;
}) {
  const [name, setName] = useState(rule.name || "");
  const [description, setDescription] = useState(rule.description || "");
  const [triggerEvent, setTriggerEvent] = useState(rule.trigger_event || catalog.events[0]?.value || "");
  const [conditions, setConditions] = useState<any[]>(rule.conditions || []);
  const [actions, setActions] = useState<any[]>(rule.actions || []);
  const [isActive, setIsActive] = useState(rule.is_active ?? true);
  const [saving, setSaving] = useState(false);
  const { data: tags = [] } = useGetTagsQuery();

  const submit = async () => {
    if (!name.trim()) {
      await notifyUser({ title: "Name required" });
      return;
    }
    if (actions.length === 0) {
      await notifyUser({ title: "At least one action is required" });
      return;
    }
    setSaving(true);
    try {
      await onSave({
        ...(rule.id ? { id: rule.id } : {}),
        name: name.trim(),
        description: description.trim() || null,
        trigger_event: triggerEvent,
        conditions,
        actions,
        is_active: isActive,
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="form-modal-root" role="dialog" aria-modal="true" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="form-modal-panel" style={{ maxWidth: 640 }}>
        <header className="form-modal-head">
          <h2 className="form-modal-title">{rule.id ? "Edit rule" : "New rule"}</h2>
          <button type="button" className="form-modal-close" onClick={onClose} aria-label="Close">
            <Icon.Close size={16} />
          </button>
        </header>
        <div className="form-modal-body">
          <div className="form-group">
            <label>Name</label>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Notify finance on big invoices" />
          </div>
          <div className="form-group">
            <label>Description</label>
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2} />
          </div>
          <div className="form-group">
            <label>Trigger event</label>
            <select value={triggerEvent} onChange={(e) => setTriggerEvent(e.target.value)}>
              {catalog.events.map((ev) => (
                <option key={ev.value} value={ev.value}>{ev.label} ({ev.value})</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
              <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
              <span>Active</span>
            </label>
          </div>

          <div style={{ marginTop: "1rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.4rem" }}>
              <strong style={{ fontSize: "0.82rem" }}>Conditions (all must match)</strong>
              <button
                type="button"
                className="btn btn-sm"
                onClick={() => setConditions([...conditions, { field: "after.amount", op: ">", value: 0 }])}
              >
                + condition
              </button>
            </div>
            {conditions.length === 0 && (
              <div style={{ fontSize: "0.78rem", color: "var(--gray-500)" }}>
                No conditions — fires on every event.
              </div>
            )}
            {conditions.map((c, i) => (
              <div key={i} style={{ display: "flex", gap: "0.3rem", marginBottom: "0.35rem" }}>
                <input
                  style={{ flex: 2, fontFamily: "monospace", fontSize: "0.78rem" }}
                  value={c.field || ""}
                  onChange={(e) => setConditions(conditions.map((x, j) => (j === i ? { ...x, field: e.target.value } : x)))}
                  placeholder="path.to.field"
                />
                <select
                  style={{ flex: 0.7 }}
                  value={c.op || "=="}
                  onChange={(e) => setConditions(conditions.map((x, j) => (j === i ? { ...x, op: e.target.value } : x)))}
                >
                  {catalog.ops.map((op) => <option key={op} value={op}>{op}</option>)}
                </select>
                <input
                  style={{ flex: 1.5 }}
                  value={c.value ?? ""}
                  onChange={(e) => setConditions(conditions.map((x, j) => (j === i ? { ...x, value: e.target.value } : x)))}
                  placeholder="value"
                />
                <button type="button" className="btn btn-sm btn-danger" onClick={() => setConditions(conditions.filter((_, j) => j !== i))}>
                  ×
                </button>
              </div>
            ))}
          </div>

          <div style={{ marginTop: "1rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.4rem" }}>
              <strong style={{ fontSize: "0.82rem" }}>Actions (in order)</strong>
              <button
                type="button"
                className="btn btn-sm"
                onClick={() => setActions([...actions, { type: catalog.actions[0]?.value || "log", params: {} }])}
              >
                + action
              </button>
            </div>
            {actions.map((a, i) => (
              <ActionRow
                key={i}
                action={a}
                catalog={catalog}
                tags={tags as any[]}
                onChange={(next) => setActions(actions.map((x, j) => (j === i ? next : x)))}
                onRemove={() => setActions(actions.filter((_, j) => j !== i))}
              />
            ))}
          </div>
        </div>
        <footer className="form-modal-foot">
          <button type="button" className="btn btn-sm" onClick={onClose} disabled={saving}>Cancel</button>
          <button type="button" className="btn btn-sm btn-primary" onClick={submit} disabled={saving}>
            {saving ? "Saving…" : "Save rule"}
          </button>
        </footer>
      </div>
    </div>
  );
}

function ActionRow({
  action,
  catalog,
  tags,
  onChange,
  onRemove,
}: {
  action: any;
  catalog: Catalog;
  tags: any[];
  onChange: (next: any) => void;
  onRemove: () => void;
}) {
  const updateParam = (key: string, value: any) =>
    onChange({ ...action, params: { ...(action.params || {}), [key]: value } });

  return (
    <div style={{ border: "1px solid var(--gray-200)", borderRadius: "var(--radius-sm)", padding: "0.5rem 0.6rem", marginBottom: "0.4rem" }}>
      <div style={{ display: "flex", gap: "0.35rem", marginBottom: "0.4rem", alignItems: "center" }}>
        <select
          style={{ flex: 1 }}
          value={action.type}
          onChange={(e) => onChange({ type: e.target.value, params: {} })}
        >
          {catalog.actions.map((a) => <option key={a.value} value={a.value}>{a.label}</option>)}
        </select>
        <button type="button" className="btn btn-sm btn-danger" onClick={onRemove}>×</button>
      </div>
      {action.type === "notify_user" && (
        <>
          <div className="form-group">
            <label style={{ fontSize: "0.72rem" }}>User ID</label>
            <input value={action.params?.user_id || ""} onChange={(e) => updateParam("user_id", e.target.value)} placeholder="UUID" />
          </div>
          <div className="form-group">
            <label style={{ fontSize: "0.72rem" }}>Title</label>
            <input value={action.params?.title || ""} onChange={(e) => updateParam("title", e.target.value)} placeholder="e.g. Big invoice created" />
          </div>
          <div className="form-group">
            <label style={{ fontSize: "0.72rem" }}>Body (supports {`{field_path}`} placeholders)</label>
            <input value={action.params?.body || ""} onChange={(e) => updateParam("body", e.target.value)} />
          </div>
        </>
      )}
      {action.type === "add_tag" && (
        <>
          <div className="form-group">
            <label style={{ fontSize: "0.72rem" }}>Tag</label>
            <select value={action.params?.tag_id || ""} onChange={(e) => updateParam("tag_id", e.target.value)}>
              <option value="">— select tag —</option>
              {tags.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select>
            <div style={{ fontSize: "0.7rem", color: "var(--gray-500)", marginTop: "0.2rem" }}>
              Defaults to the event's entity_type / entity_id; override below if needed.
            </div>
          </div>
        </>
      )}
      {action.type === "post_webhook" && (
        <div className="form-group">
          <label style={{ fontSize: "0.72rem" }}>URL</label>
          <input value={action.params?.url || ""} onChange={(e) => updateParam("url", e.target.value)} placeholder="https://hooks.example.com/..." />
        </div>
      )}
      {action.type === "log" && (
        <div className="form-group">
          <label style={{ fontSize: "0.72rem" }}>Message (supports {`{field}`} placeholders)</label>
          <input value={action.params?.message || ""} onChange={(e) => updateParam("message", e.target.value)} />
        </div>
      )}
    </div>
  );
}
