import { useState } from "react";
import { useParams } from "react-router-dom";
import {
  useGetTasksQuery,
  useGetCpmQuery,
  useGetPertQuery,
  useGetDependenciesQuery,
  useCreateDependencyMutation,
  useDeleteDependencyMutation,
} from "../services/api";

export default function SchedulePage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { data: tasks = [] } = useGetTasksQuery(projectId!);
  const { data: cpm, isLoading: cpmLoading } = useGetCpmQuery(projectId!);
  const [targets, setTargets] = useState("");
  const { data: pert } = useGetPertQuery({ projectId: projectId!, targets });
  const { data: deps = [] } = useGetDependenciesQuery(projectId!);
  const [createDep] = useCreateDependencyMutation();
  const [deleteDep] = useDeleteDependencyMutation();
  const [tab, setTab] = useState<"cpm" | "pert" | "deps">("cpm");
  const [depForm, setDepForm] = useState({ predecessor_id: "", successor_id: "", dependency_type: "finish_to_start", lag_days: 0 });

  const handleAddDep = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!depForm.predecessor_id || !depForm.successor_id) return;
    await createDep({ ...depForm, project_id: projectId });
    setDepForm({ predecessor_id: "", successor_id: "", dependency_type: "finish_to_start", lag_days: 0 });
  };

  const criticalIds = new Set(cpm?.critical_path || []);

  return (
    <div>
      <h2 style={{ marginBottom: "0.5rem" }}>Schedule Analysis (CPM / PERT)</h2>
      <p style={{ color: "var(--gray-500)", marginBottom: "1rem", fontSize: "0.9rem" }}>
        Critical Path Method and Program Evaluation Review Technique (PMBOK 2.4 Planning)
      </p>

      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1.5rem" }}>
        {(["cpm", "pert", "deps"] as const).map((t) => (
          <button key={t} className={`btn ${tab === t ? "btn-primary" : ""}`} onClick={() => setTab(t)}>
            {t === "cpm" ? "CPM Analysis" : t === "pert" ? "PERT Analysis" : "Dependencies"}
          </button>
        ))}
      </div>

      {/* ── CPM Tab ─────────────────────────────── */}
      {tab === "cpm" && (
        <>
          {cpmLoading ? <p>Calculating...</p> : !cpm || cpm.tasks.length === 0 ? (
            <div className="empty-state"><p>Add tasks with durations and dependencies to see CPM analysis.</p></div>
          ) : (
            <>
              {cpm.has_cycle && <div className="auth-error">{cpm.cycle_message}</div>}

              <div className="stats-grid">
                <div className="stat-card">
                  <div className="label">Project Duration</div>
                  <div className="value">{cpm.project_duration} days</div>
                </div>
                <div className="stat-card">
                  <div className="label">Critical Tasks</div>
                  <div className="value">{cpm.critical_path.length}</div>
                </div>
                <div className="stat-card">
                  <div className="label">Total Tasks</div>
                  <div className="value">{cpm.tasks.length}</div>
                </div>
              </div>

              {/* Network diagram (text-based) */}
              {cpm.critical_path.length > 0 && (
                <div className="card" style={{ marginBottom: "1rem" }}>
                  <h3 style={{ marginBottom: "0.75rem" }}>Critical Path</h3>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", alignItems: "center" }}>
                    {cpm.tasks.filter((t: any) => t.is_critical).map((t: any, i: number, arr: any[]) => (
                      <span key={t.id} style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                        <span className="badge badge-red" style={{ padding: "0.4rem 0.8rem", fontSize: "0.85rem" }}>
                          {t.title} ({t.duration}d)
                        </span>
                        {i < arr.length - 1 && <span style={{ color: "var(--gray-500)", fontSize: "1.2rem" }}>→</span>}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <div className="card">
                <h3 style={{ marginBottom: "0.75rem" }}>CPM Schedule Table</h3>
                <div style={{ overflowX: "auto" }}>
                  <table>
                    <thead>
                      <tr>
                        <th>Task</th><th>Duration</th><th>ES</th><th>EF</th>
                        <th>LS</th><th>LF</th><th>Total Float</th><th>Free Float</th><th>Critical</th>
                      </tr>
                    </thead>
                    <tbody>
                      {cpm.tasks.map((t: any) => (
                        <tr key={t.id} style={{ background: t.is_critical ? "#fee2e2" : undefined }}>
                          <td style={{ fontWeight: t.is_critical ? 600 : 400 }}>{t.title}</td>
                          <td>{t.duration}</td>
                          <td>{t.es}</td><td>{t.ef}</td>
                          <td>{t.ls}</td><td>{t.lf}</td>
                          <td><span className={`badge ${t.total_float === 0 ? "badge-red" : "badge-green"}`}>{t.total_float}</span></td>
                          <td>{t.free_float}</td>
                          <td>{t.is_critical ? <span className="badge badge-red">YES</span> : <span className="badge badge-gray">no</span>}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}
        </>
      )}

      {/* ── PERT Tab ────────────────────────────── */}
      {tab === "pert" && (
        <>
          {!pert || pert.tasks.length === 0 ? (
            <div className="empty-state"><p>Add tasks with 3-point estimates (O, M, P) to see PERT analysis.</p></div>
          ) : (
            <>
              <div className="stats-grid">
                <div className="stat-card">
                  <div className="label">Expected Duration (Te)</div>
                  <div className="value">{pert.project_expected_duration} days</div>
                </div>
                <div className="stat-card">
                  <div className="label">Std Deviation (σ)</div>
                  <div className="value">{pert.project_std_dev}</div>
                </div>
                <div className="stat-card">
                  <div className="label">Variance (σ²)</div>
                  <div className="value">{pert.project_variance}</div>
                </div>
              </div>

              {/* Probability calculator */}
              <div className="card" style={{ marginBottom: "1rem" }}>
                <h3 style={{ marginBottom: "0.75rem" }}>Completion Probability Calculator</h3>
                <div style={{ display: "flex", gap: "0.75rem", alignItems: "flex-end", flexWrap: "wrap" }}>
                  <div className="form-group" style={{ marginBottom: 0 }}>
                    <label>Target Durations (comma-separated days)</label>
                    <input
                      value={targets}
                      onChange={(e) => setTargets(e.target.value)}
                      placeholder="e.g. 30,35,40,45"
                      style={{ width: 280 }}
                    />
                  </div>
                </div>
                {Object.keys(pert.completion_probabilities || {}).length > 0 && (
                  <table style={{ marginTop: "1rem" }}>
                    <thead><tr><th>Target (days)</th><th>Probability</th><th>Visualization</th></tr></thead>
                    <tbody>
                      {Object.entries(pert.completion_probabilities).map(([dur, prob]: [string, any]) => (
                        <tr key={dur}>
                          <td>{dur}</td>
                          <td><span className={`badge ${prob >= 80 ? "badge-green" : prob >= 50 ? "badge-yellow" : "badge-red"}`}>{prob}%</span></td>
                          <td>
                            <div className="progress-bar" style={{ width: 200 }}>
                              <div className="fill" style={{ width: `${Math.min(prob, 100)}%`, background: prob >= 80 ? "var(--success)" : prob >= 50 ? "var(--warning)" : "var(--danger)" }} />
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>

              <div className="card">
                <h3 style={{ marginBottom: "0.75rem" }}>PERT Estimates Table</h3>
                <p style={{ fontSize: "0.85rem", color: "var(--gray-500)", marginBottom: "0.75rem" }}>
                  Te = (O + 4M + P) / 6 &nbsp;|&nbsp; σ = (P - O) / 6
                </p>
                <div style={{ overflowX: "auto" }}>
                  <table>
                    <thead>
                      <tr>
                        <th>Task</th><th>Optimistic (O)</th><th>Most Likely (M)</th><th>Pessimistic (P)</th>
                        <th>Expected (Te)</th><th>Std Dev (σ)</th><th>Variance (σ²)</th><th>Critical</th>
                      </tr>
                    </thead>
                    <tbody>
                      {pert.tasks.map((t: any) => (
                        <tr key={t.id} style={{ background: t.is_critical ? "#fee2e2" : undefined }}>
                          <td style={{ fontWeight: t.is_critical ? 600 : 400 }}>{t.title}</td>
                          <td>{t.optimistic ?? "-"}</td>
                          <td>{t.most_likely ?? "-"}</td>
                          <td>{t.pessimistic ?? "-"}</td>
                          <td><strong>{t.pert_expected ?? "-"}</strong></td>
                          <td>{t.pert_std_dev ?? "-"}</td>
                          <td>{t.pert_variance ?? "-"}</td>
                          <td>{t.is_critical ? <span className="badge badge-red">YES</span> : <span className="badge badge-gray">no</span>}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}
        </>
      )}

      {/* ── Dependencies Tab ────────────────────── */}
      {tab === "deps" && (
        <>
          <div className="card" style={{ marginBottom: "1rem" }}>
            <h3 style={{ marginBottom: "0.75rem" }}>Add Dependency</h3>
            <form onSubmit={handleAddDep}>
              <div className="form-row">
                <div className="form-group">
                  <label>Predecessor</label>
                  <select value={depForm.predecessor_id} onChange={(e) => setDepForm({ ...depForm, predecessor_id: e.target.value })}>
                    <option value="">Select task...</option>
                    {tasks.map((t: any) => <option key={t.id} value={t.id}>{t.title}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label>Successor</label>
                  <select value={depForm.successor_id} onChange={(e) => setDepForm({ ...depForm, successor_id: e.target.value })}>
                    <option value="">Select task...</option>
                    {tasks.map((t: any) => <option key={t.id} value={t.id}>{t.title}</option>)}
                  </select>
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Type</label>
                  <select value={depForm.dependency_type} onChange={(e) => setDepForm({ ...depForm, dependency_type: e.target.value })}>
                    <option value="finish_to_start">Finish-to-Start (FS)</option>
                    <option value="finish_to_finish">Finish-to-Finish (FF)</option>
                    <option value="start_to_start">Start-to-Start (SS)</option>
                    <option value="start_to_finish">Start-to-Finish (SF)</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Lag (days)</label>
                  <input type="number" value={depForm.lag_days} onChange={(e) => setDepForm({ ...depForm, lag_days: +e.target.value })} />
                </div>
              </div>
              <button type="submit" className="btn btn-primary">Add Dependency</button>
            </form>
          </div>

          {deps.length === 0 ? (
            <div className="empty-state"><p>No dependencies defined yet.</p></div>
          ) : (
            <div className="card">
              <table>
                <thead><tr><th>Predecessor</th><th>→</th><th>Successor</th><th>Type</th><th>Lag</th><th>Actions</th></tr></thead>
                <tbody>
                  {deps.map((d: any) => {
                    const pred = tasks.find((t: any) => t.id === d.predecessor_id);
                    const succ = tasks.find((t: any) => t.id === d.successor_id);
                    return (
                      <tr key={d.id}>
                        <td>{pred?.title || d.predecessor_id}</td>
                        <td>→</td>
                        <td>{succ?.title || d.successor_id}</td>
                        <td><span className="badge badge-blue">{d.dependency_type.replace(/_/g, " ")}</span></td>
                        <td>{d.lag_days}d</td>
                        <td><button className="btn btn-danger btn-sm" onClick={() => deleteDep({ projectId: projectId!, depId: d.id })}>Delete</button></td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
