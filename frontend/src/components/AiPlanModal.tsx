import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import {
  useStartAiPlanMutation,
  useCommitAiPlanMutation,
  useGetCeleryTaskResultQuery,
} from "../services/api";
import { Icon } from "../shell/icons";

type AiPlanModalProps = {
  open: boolean;
  projectId: string;
  onClose: () => void;
  onCommitted?: (created: { tasks: number; risks: number; deliverables: number; milestones: number }) => void;
};

type Plan = {
  source?: string;
  summary?: string;
  tasks?: { title: string; description?: string; estimate_hours?: number }[];
  risks?: { title: string; impact?: string; likelihood?: string }[];
  milestones?: { title: string; target_offset_days?: number }[];
  deliverables?: { title: string; description?: string }[];
};

export default function AiPlanModal({ open, projectId, onClose, onCommitted }: AiPlanModalProps) {
  const [brief, setBrief] = useState("");
  const [taskId, setTaskId] = useState<string | null>(null);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [start, { isLoading: starting }] = useStartAiPlanMutation();
  const [commit, { isLoading: committing }] = useCommitAiPlanMutation();
  const { data: taskResult } = useGetCeleryTaskResultQuery(taskId || "", {
    skip: !taskId || !!plan,
    pollingInterval: taskId && !plan ? 1500 : 0,
  });

  useEffect(() => {
    if (!taskResult) return;
    if (taskResult.status === "SUCCESS") {
      setPlan(taskResult.result || null);
    } else if (taskResult.status === "FAILURE") {
      setError(taskResult.error || "Generation failed");
      setTaskId(null);
    }
  }, [taskResult]);

  const reset = () => {
    setBrief("");
    setTaskId(null);
    setPlan(null);
    setError(null);
  };

  const onCloseAndReset = () => {
    reset();
    onClose();
  };

  const submitBrief = async () => {
    setError(null);
    if (!brief.trim()) return;
    const r: any = await start({ projectId, brief: brief.trim() });
    if (r.error) {
      setError((r.error as any)?.data?.detail || "Failed to start");
      return;
    }
    setTaskId(r.data.task_id);
  };

  const accept = async () => {
    if (!plan) return;
    const r: any = await commit({ projectId, plan });
    if (r.error) {
      setError((r.error as any)?.data?.detail || "Commit failed");
      return;
    }
    onCommitted?.(r.data.created);
    reset();
    onClose();
  };

  if (!open) return null;
  const node = (
    <div
      className="form-modal-root"
      role="dialog"
      aria-modal="true"
      onClick={(e) => { if (e.target === e.currentTarget) onCloseAndReset(); }}
    >
      <div className="form-modal-panel" style={{ maxWidth: 720 }}>
        <header className="form-modal-head">
          <h2 className="form-modal-title">
            <Icon.Zap size={16} style={{ marginRight: "0.4rem", verticalAlign: "-2px" }} />
            AI plan from brief
          </h2>
          <button type="button" className="form-modal-close" onClick={onCloseAndReset} aria-label="Close">
            <Icon.Close size={16} />
          </button>
        </header>
        <div className="form-modal-body">
          {error && <div className="form-modal-error">{error}</div>}

          {!plan && !taskId && (
            <>
              <p style={{ fontSize: "0.82rem", color: "var(--gray-600)", marginBottom: "0.5rem" }}>
                Describe the project in plain English. The model will return a draft WBS — tasks, risks, deliverables, milestones — that you can review before committing.
              </p>
              <div className="form-group">
                <label>Project brief</label>
                <textarea
                  value={brief}
                  onChange={(e) => setBrief(e.target.value)}
                  rows={6}
                  placeholder="e.g. Launch a new B2B SaaS product targeting mid-market HR teams. 6-month timeline, 4 engineers + 1 designer + 1 PM."
                />
              </div>
              <button
                className="btn btn-sm btn-primary"
                onClick={submitBrief}
                disabled={starting || !brief.trim()}
              >
                {starting ? "Submitting…" : "Generate plan"}
              </button>
            </>
          )}

          {taskId && !plan && (
            <div style={{ padding: "1.5rem 0", textAlign: "center", color: "var(--gray-500)" }}>
              <div style={{ fontSize: "0.95rem", fontWeight: 600, marginBottom: "0.4rem" }}>Generating…</div>
              <div style={{ fontSize: "0.78rem" }}>
                LLM calls can take 10–60 seconds. We'll poll the task and show the plan as soon as it's ready.
              </div>
            </div>
          )}

          {plan && (
            <PlanReview plan={plan} onChange={setPlan} />
          )}
        </div>
        <footer className="form-modal-foot">
          <button type="button" className="btn btn-sm" onClick={onCloseAndReset} disabled={committing}>
            {plan ? "Discard" : "Cancel"}
          </button>
          {plan && (
            <button
              type="button"
              className="btn btn-sm btn-primary"
              onClick={accept}
              disabled={committing}
            >
              {committing ? "Saving…" : "Accept & create"}
            </button>
          )}
        </footer>
      </div>
    </div>
  );
  return createPortal(node, document.body);
}

function PlanReview({ plan, onChange }: { plan: Plan; onChange: (p: Plan) => void }) {
  const removeFrom = (key: keyof Plan, idx: number) => {
    const list = ((plan as any)[key] || []).filter((_: any, i: number) => i !== idx);
    onChange({ ...plan, [key]: list });
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.85rem" }}>
      {plan.source && (
        <div style={{ fontSize: "0.72rem", color: "var(--gray-500)" }}>
          Source: <code>{plan.source}</code> {plan.source.startsWith("mock") && <span>(set <code>LLM_API_KEY</code> for real LLM output)</span>}
        </div>
      )}
      {plan.summary && (
        <div className="card" style={{ padding: "0.75rem", marginBottom: 0 }}>
          <div style={{ fontSize: "0.72rem", color: "var(--gray-500)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Summary</div>
          <div style={{ fontSize: "0.85rem", marginTop: "0.25rem" }}>{plan.summary}</div>
        </div>
      )}
      <PlanSection title={`Tasks (${plan.tasks?.length || 0})`} items={plan.tasks || []} render={(t: any) => (
        <>
          <strong>{t.title}</strong>
          {t.estimate_hours !== undefined && <span style={{ marginLeft: "0.4rem", color: "var(--gray-500)" }}>~{t.estimate_hours}h</span>}
          {t.description && <div style={{ fontSize: "0.78rem", color: "var(--gray-500)" }}>{t.description}</div>}
        </>
      )} onRemove={(i) => removeFrom("tasks", i)} />
      <PlanSection title={`Milestones (${plan.milestones?.length || 0})`} items={plan.milestones || []} render={(m: any) => (
        <>
          <strong>🎯 {m.title}</strong>
          {m.target_offset_days != null && <span style={{ marginLeft: "0.4rem", color: "var(--gray-500)" }}>+{m.target_offset_days}d</span>}
        </>
      )} onRemove={(i) => removeFrom("milestones", i)} />
      <PlanSection title={`Risks (${plan.risks?.length || 0})`} items={plan.risks || []} render={(r: any) => (
        <>
          <strong>{r.title}</strong>
          <span className="badge badge-gray" style={{ marginLeft: "0.4rem" }}>{r.impact}/{r.likelihood}</span>
        </>
      )} onRemove={(i) => removeFrom("risks", i)} />
      <PlanSection title={`Deliverables (${plan.deliverables?.length || 0})`} items={plan.deliverables || []} render={(d: any) => (
        <>
          <strong>{d.title}</strong>
          {d.description && <div style={{ fontSize: "0.78rem", color: "var(--gray-500)" }}>{d.description}</div>}
        </>
      )} onRemove={(i) => removeFrom("deliverables", i)} />
    </div>
  );
}

function PlanSection({
  title,
  items,
  render,
  onRemove,
}: {
  title: string;
  items: any[];
  render: (item: any) => React.ReactNode;
  onRemove: (idx: number) => void;
}) {
  if (items.length === 0) return null;
  return (
    <div>
      <div style={{ fontSize: "0.78rem", fontWeight: 600, color: "var(--gray-700)", marginBottom: "0.35rem" }}>{title}</div>
      <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "0.25rem" }}>
        {items.map((it, i) => (
          <li
            key={i}
            style={{
              padding: "0.4rem 0.55rem",
              border: "1px solid var(--gray-200)",
              borderRadius: "var(--radius-sm)",
              fontSize: "0.82rem",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "flex-start",
              gap: "0.5rem",
            }}
          >
            <div style={{ flex: 1, minWidth: 0 }}>{render(it)}</div>
            <button
              className="btn btn-sm"
              onClick={() => onRemove(i)}
              title="Remove from plan"
              style={{ flexShrink: 0 }}
            >
              ×
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
