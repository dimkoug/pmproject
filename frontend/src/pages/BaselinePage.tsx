import { useState } from "react";
import { useParams } from "react-router-dom";
import { useGetBaselinesQuery, useSaveBaselineMutation, useCompareBaselineQuery } from "../services/api";

export default function BaselinePage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { data: baselines = [], refetch } = useGetBaselinesQuery(projectId!);
  const [save] = useSaveBaselineMutation();
  const [name, setName] = useState("");
  const [compareId, setCompareId] = useState("");
  const { data: comparison } = useCompareBaselineQuery(
    { projectId: projectId!, baselineId: compareId },
    { skip: !compareId }
  );

  const handleSave = async () => {
    if (!name) return;
    await save({ projectId: projectId!, name });
    setName("");
    refetch();
  };

  return (
    <div>
      <div style={{ marginBottom: "1.5rem" }}>
        <h2 style={{ fontSize: "1.4rem", fontWeight: 700, marginBottom: "0.3rem" }}>Schedule Baselines</h2>
        <p style={{ color: "var(--gray-400)", fontSize: "0.85rem" }}>Save schedule snapshots and compare actual vs planned</p>
      </div>

      <div className="card" style={{ marginBottom: "1.25rem" }}>
        <h3 style={{ marginBottom: "0.75rem" }}>Save Current Schedule as Baseline</h3>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "flex-end" }}>
          <div className="form-group" style={{ flex: 1, marginBottom: 0 }}>
            <label>Baseline Name</label>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Sprint 3 Baseline" style={{ width: "100%", padding: "0.45rem 0.65rem", border: "1px solid var(--gray-300)", borderRadius: "var(--radius)", fontSize: "0.835rem" }} />
          </div>
          <button className="btn btn-primary" onClick={handleSave} disabled={!name}>Save Baseline</button>
        </div>
      </div>

      {baselines.length > 0 && (
        <div className="card" style={{ marginBottom: "1.25rem" }}>
          <h3 style={{ marginBottom: "0.75rem" }}>Saved Baselines</h3>
          <table>
            <thead><tr><th>Name</th><th>Duration</th><th>Tasks</th><th>Saved</th><th>Actions</th></tr></thead>
            <tbody>
              {baselines.map((b: any) => (
                <tr key={b.id}>
                  <td style={{ fontWeight: 500 }}>{b.name}</td>
                  <td>{b.project_duration}d</td>
                  <td>{b.task_count}</td>
                  <td style={{ fontSize: "0.82rem", color: "var(--gray-500)" }}>{new Date(b.created_at).toLocaleDateString()}</td>
                  <td><button className={`btn btn-sm ${compareId === b.id ? "btn-primary" : ""}`} onClick={() => setCompareId(compareId === b.id ? "" : b.id)}>Compare</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {comparison && (
        <div className="card">
          <h3 style={{ marginBottom: "0.75rem" }}>Comparison: {comparison.baseline_name} vs Current</h3>
          <div className="stats-grid" style={{ marginBottom: "1rem" }}>
            <div className="stat-card"><div className="label">Baseline Duration</div><div className="value">{comparison.baseline_duration}d</div></div>
            <div className="stat-card"><div className="label">Current Duration</div><div className="value">{comparison.current_duration}d</div></div>
            <div className="stat-card">
              <div className="label">Variance</div>
              <div className="value" style={{ color: comparison.variance > 0 ? "var(--danger)" : comparison.variance < 0 ? "var(--success)" : "var(--gray-700)" }}>
                {comparison.variance > 0 ? "+" : ""}{comparison.variance}d
              </div>
            </div>
          </div>
          <div style={{ overflowX: "auto" }}>
            <table>
              <thead><tr><th>Task</th><th>Base Dur</th><th>Curr Dur</th><th>Base EF</th><th>Curr EF</th><th>Duration Var</th><th>Schedule Var</th></tr></thead>
              <tbody>
                {comparison.tasks.filter((t: any) => t.baseline_duration != null || t.current_duration != null).map((t: any) => (
                  <tr key={t.id}>
                    <td style={{ fontWeight: 500 }}>{t.title}</td>
                    <td>{t.baseline_duration ?? "-"}</td>
                    <td>{t.current_duration ?? "-"}</td>
                    <td>{t.baseline_ef ?? "-"}</td>
                    <td>{t.current_ef ?? "-"}</td>
                    <td style={{ color: (t.duration_variance || 0) > 0 ? "var(--danger)" : "var(--success)" }}>{t.duration_variance != null ? `${t.duration_variance > 0 ? "+" : ""}${t.duration_variance}d` : "-"}</td>
                    <td style={{ color: (t.schedule_variance || 0) > 0 ? "var(--danger)" : "var(--success)" }}>{t.schedule_variance != null ? `${t.schedule_variance > 0 ? "+" : ""}${t.schedule_variance}d` : "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
