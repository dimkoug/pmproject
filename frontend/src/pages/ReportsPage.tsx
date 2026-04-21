import { useState } from "react";
import { useParams } from "react-router-dom";
import {
  useGetReportSummaryQuery,
  useGetReportScheduleQuery,
  useGetReportRisksQuery,
  useGetReportPerformanceQuery,
} from "../services/api";

const RISK_COLORS: Record<string, string> = {
  very_low: "#dcfce7", low: "#bbf7d0", medium: "#fef3c7", high: "#fed7aa", very_high: "#fecaca",
};

export default function ReportsPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [tab, setTab] = useState<"summary" | "schedule" | "risks" | "performance">("summary");

  const { data: summary } = useGetReportSummaryQuery(projectId!, { skip: tab !== "summary" });
  const { data: schedule } = useGetReportScheduleQuery(projectId!, { skip: tab !== "schedule" });
  const { data: riskReport } = useGetReportRisksQuery(projectId!, { skip: tab !== "risks" });
  const { data: perf } = useGetReportPerformanceQuery(projectId!, { skip: tab !== "performance" });

  return (
    <div>
      <h2 style={{ marginBottom: "0.5rem" }}>Project Reports</h2>
      <p style={{ color: "var(--gray-500)", marginBottom: "1rem", fontSize: "0.9rem" }}>
        Comprehensive project analysis across all PMBOK performance domains
        <a
          href={`${import.meta.env.VITE_API_URL || "http://localhost:8000"}/api/projects/${projectId}/export/excel`}
          className="btn btn-primary btn-sm"
          style={{ marginLeft: "1rem", textDecoration: "none" }}
          target="_blank"
        >
          Export Excel
        </a>
      </p>

      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1.5rem" }}>
        {(["summary", "schedule", "risks", "performance"] as const).map((t) => (
          <button key={t} className={`btn ${tab === t ? "btn-primary" : ""}`} onClick={() => setTab(t)}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {/* ── Summary Report ────────────────────── */}
      {tab === "summary" && summary && (
        <>
          <div className="card" style={{ marginBottom: "1rem" }}>
            <h3 style={{ marginBottom: "0.75rem" }}>Project Overview</h3>
            <table>
              <tbody>
                <tr><td style={{ fontWeight: 600, width: 180 }}>Name</td><td>{summary.project.name}</td></tr>
                <tr><td style={{ fontWeight: 600 }}>Status</td><td><span className="badge badge-blue">{summary.project.status}</span></td></tr>
                <tr><td style={{ fontWeight: 600 }}>Approach</td><td>{summary.project.development_approach}</td></tr>
                <tr><td style={{ fontWeight: 600 }}>Budget</td><td>${summary.project.budget?.toLocaleString()}</td></tr>
              </tbody>
            </table>
          </div>

          <div className="stats-grid">
            <div className="stat-card">
              <div className="label">Task Completion</div>
              <div className="value">{summary.tasks.completion_pct}%</div>
              <div className="progress-bar" style={{ marginTop: "0.5rem" }}><div className="fill" style={{ width: `${summary.tasks.completion_pct}%` }} /></div>
              <div style={{ fontSize: "0.8rem", color: "var(--gray-500)", marginTop: "0.25rem" }}>{summary.tasks.done} / {summary.tasks.total} tasks</div>
            </div>
            <div className="stat-card">
              <div className="label">Open Risks</div>
              <div className="value" style={{ color: summary.risks.open > 0 ? "var(--danger)" : "var(--success)" }}>{summary.risks.open}</div>
              <div style={{ fontSize: "0.8rem", color: "var(--gray-500)" }}>{summary.risks.total} total</div>
            </div>
            <div className="stat-card">
              <div className="label">Deliverable Acceptance</div>
              <div className="value">{summary.deliverables.acceptance_pct}%</div>
              <div style={{ fontSize: "0.8rem", color: "var(--gray-500)" }}>{summary.deliverables.accepted} / {summary.deliverables.total}</div>
            </div>
            <div className="stat-card">
              <div className="label">Pending Changes</div>
              <div className="value">{summary.change_requests.pending}</div>
              <div style={{ fontSize: "0.8rem", color: "var(--gray-500)" }}>{summary.change_requests.total} total</div>
            </div>
          </div>

          {summary.risks.high_impact.length > 0 && (
            <div className="card">
              <h3 style={{ marginBottom: "0.75rem" }}>High-Impact Risks</h3>
              <table>
                <thead><tr><th>Title</th><th>Probability</th><th>Impact</th><th>Status</th></tr></thead>
                <tbody>
                  {summary.risks.high_impact.map((r: any, i: number) => (
                    <tr key={i}><td>{r.title}</td><td><span className="badge badge-yellow">{r.probability}</span></td><td><span className="badge badge-red">{r.impact}</span></td><td>{r.status}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {/* ── Schedule Report ───────────────────── */}
      {tab === "schedule" && schedule && (
        <>
          <div className="stats-grid">
            <div className="stat-card">
              <div className="label">Project Duration (CPM)</div>
              <div className="value">{schedule.cpm.project_duration} days</div>
            </div>
            <div className="stat-card">
              <div className="label">Expected Duration (PERT)</div>
              <div className="value">{schedule.pert.expected_duration} days</div>
            </div>
            <div className="stat-card">
              <div className="label">Std Deviation</div>
              <div className="value">{schedule.pert.std_dev}</div>
            </div>
            <div className="stat-card">
              <div className="label">Variance</div>
              <div className="value">{schedule.pert.variance}</div>
            </div>
          </div>

          {schedule.cpm.has_cycle && <div className="auth-error">Circular dependency detected!</div>}

          {schedule.cpm.critical_path.length > 0 && (
            <div className="card" style={{ marginBottom: "1rem" }}>
              <h3 style={{ marginBottom: "0.75rem" }}>Critical Path</h3>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", alignItems: "center" }}>
                {schedule.cpm.critical_path.map((t: any, i: number, arr: any[]) => (
                  <span key={t.id} style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <span className="badge badge-red" style={{ padding: "0.4rem 0.8rem" }}>{t.title} ({t.duration}d)</span>
                    {i < arr.length - 1 && <span style={{ color: "var(--gray-500)", fontSize: "1.2rem" }}>→</span>}
                  </span>
                ))}
              </div>
            </div>
          )}

          {Object.keys(schedule.pert.completion_probabilities || {}).length > 0 && (
            <div className="card" style={{ marginBottom: "1rem" }}>
              <h3 style={{ marginBottom: "0.75rem" }}>Completion Probability</h3>
              <table>
                <thead><tr><th>Target (days)</th><th>Probability</th></tr></thead>
                <tbody>
                  {Object.entries(schedule.pert.completion_probabilities).map(([d, p]: [string, any]) => (
                    <tr key={d}><td>{d}</td><td><span className={`badge ${p >= 80 ? "badge-green" : p >= 50 ? "badge-yellow" : "badge-red"}`}>{p}%</span></td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="card" style={{ marginBottom: "1rem" }}>
            <h3 style={{ marginBottom: "0.75rem" }}>Full Schedule Table</h3>
            <div style={{ overflowX: "auto" }}>
              <table>
                <thead><tr><th>Task</th><th>Status</th><th>Duration</th><th>ES</th><th>EF</th><th>LS</th><th>LF</th><th>Float</th><th>PERT Te</th><th>Critical</th></tr></thead>
                <tbody>
                  {schedule.tasks.map((t: any) => (
                    <tr key={t.id} style={{ background: t.is_critical ? "#fee2e2" : undefined }}>
                      <td style={{ fontWeight: t.is_critical ? 600 : 400 }}>{t.title}</td>
                      <td><span className="badge badge-blue">{t.status}</span></td>
                      <td>{t.duration}</td>
                      <td>{t.es}</td><td>{t.ef}</td><td>{t.ls}</td><td>{t.lf}</td>
                      <td><span className={`badge ${t.total_float === 0 ? "badge-red" : "badge-green"}`}>{t.total_float}</span></td>
                      <td>{t.pert_expected ?? "-"}</td>
                      <td>{t.is_critical ? <span className="badge badge-red">YES</span> : "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {(schedule.warnings.tasks_missing_duration.length > 0 || schedule.warnings.orphan_tasks.length > 0) && (
            <div className="card">
              <h3 style={{ marginBottom: "0.75rem" }}>Warnings</h3>
              {schedule.warnings.tasks_missing_duration.length > 0 && (
                <div style={{ marginBottom: "0.75rem" }}>
                  <strong>Tasks without duration estimates:</strong>
                  <ul style={{ margin: "0.25rem 0 0 1.5rem", fontSize: "0.9rem" }}>
                    {schedule.warnings.tasks_missing_duration.map((t: string, i: number) => <li key={i}>{t}</li>)}
                  </ul>
                </div>
              )}
              {schedule.warnings.orphan_tasks.length > 0 && (
                <div>
                  <strong>Tasks without dependencies (orphans):</strong>
                  <ul style={{ margin: "0.25rem 0 0 1.5rem", fontSize: "0.9rem" }}>
                    {schedule.warnings.orphan_tasks.map((t: string, i: number) => <li key={i}>{t}</li>)}
                  </ul>
                </div>
              )}
            </div>
          )}
        </>
      )}

      {/* ── Risk Report ───────────────────────── */}
      {tab === "risks" && riskReport && (
        <>
          <div className="stats-grid">
            <div className="stat-card">
              <div className="label">Total Risks</div>
              <div className="value">{riskReport.total_risks}</div>
            </div>
            <div className="stat-card">
              <div className="label">Open Risks</div>
              <div className="value" style={{ color: "var(--danger)" }}>{riskReport.open_risks}</div>
            </div>
          </div>

          <div className="card" style={{ marginBottom: "1rem" }}>
            <h3 style={{ marginBottom: "0.75rem" }}>Risk Matrix (Probability x Impact)</h3>
            <div style={{ overflowX: "auto" }}>
              <table style={{ textAlign: "center" }}>
                <thead>
                  <tr><th>P \ I</th>{["very_low", "low", "medium", "high", "very_high"].map(i => <th key={i}>{i.replace(/_/g, " ")}</th>)}</tr>
                </thead>
                <tbody>
                  {["very_high", "high", "medium", "low", "very_low"].map(p => (
                    <tr key={p}>
                      <td style={{ fontWeight: 600 }}>{p.replace(/_/g, " ")}</td>
                      {["very_low", "low", "medium", "high", "very_high"].map(i => {
                        const count = riskReport.risk_matrix[p]?.[i] || 0;
                        const scoreMap: Record<string, number> = { very_low: 1, low: 2, medium: 3, high: 4, very_high: 5 };
                        const score = scoreMap[p] * scoreMap[i];
                        const bg = score >= 16 ? "#fecaca" : score >= 9 ? "#fed7aa" : score >= 4 ? "#fef3c7" : "#dcfce7";
                        return <td key={i} style={{ background: bg, fontWeight: count > 0 ? 700 : 400 }}>{count || ""}</td>;
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="form-row" style={{ marginBottom: "1rem" }}>
            <div className="card">
              <h3 style={{ marginBottom: "0.5rem" }}>By Category</h3>
              {Object.entries(riskReport.by_category).map(([k, v]: [string, any]) => (
                <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "0.3rem 0", borderBottom: "1px solid var(--gray-100)" }}>
                  <span>{k.replace(/_/g, " ")}</span><span className="badge badge-gray">{v}</span>
                </div>
              ))}
            </div>
            <div className="card">
              <h3 style={{ marginBottom: "0.5rem" }}>By Strategy</h3>
              {Object.entries(riskReport.by_strategy).map(([k, v]: [string, any]) => (
                <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "0.3rem 0", borderBottom: "1px solid var(--gray-100)" }}>
                  <span>{k}</span><span className="badge badge-gray">{v}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="card">
            <h3 style={{ marginBottom: "0.75rem" }}>Risk Register (by Score)</h3>
            <div style={{ overflowX: "auto" }}>
              <table>
                <thead><tr><th>Title</th><th>Category</th><th>P</th><th>I</th><th>Score</th><th>Strategy</th><th>Status</th></tr></thead>
                <tbody>
                  {riskReport.risks.map((r: any) => (
                    <tr key={r.id}>
                      <td>{r.title}</td>
                      <td><span className="badge badge-gray">{r.category.replace(/_/g, " ")}</span></td>
                      <td><span className="badge badge-yellow">{r.probability.replace(/_/g, " ")}</span></td>
                      <td><span className={`badge ${r.score >= 16 ? "badge-red" : r.score >= 9 ? "badge-yellow" : "badge-green"}`}>{r.impact.replace(/_/g, " ")}</span></td>
                      <td><strong>{r.score}</strong></td>
                      <td>{r.strategy}</td>
                      <td><span className="badge badge-blue">{r.status}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* ── Performance Report ────────────────── */}
      {tab === "performance" && perf && (
        <>
          <div className="stats-grid">
            <div className="stat-card">
              <div className="label">Task Completion</div>
              <div className="value">{perf.task_performance.completion_pct}%</div>
              <div className="progress-bar" style={{ marginTop: "0.5rem" }}><div className="fill" style={{ width: `${perf.task_performance.completion_pct}%` }} /></div>
            </div>
            <div className="stat-card">
              <div className="label">Story Points Velocity</div>
              <div className="value">{perf.task_performance.done_story_points} / {perf.task_performance.total_story_points}</div>
              <div style={{ fontSize: "0.8rem", color: "var(--gray-500)" }}>{perf.task_performance.velocity_pct}% complete</div>
            </div>
            <div className="stat-card">
              <div className="label">Blocked Tasks</div>
              <div className="value" style={{ color: perf.task_performance.blocked_tasks > 0 ? "var(--danger)" : "var(--success)" }}>{perf.task_performance.blocked_tasks}</div>
            </div>
            <div className="stat-card">
              <div className="label">Avg Deliverable Completion</div>
              <div className="value">{perf.deliverable_performance.avg_completion_pct}%</div>
            </div>
          </div>

          {perf.kpis.length > 0 && (
            <div className="card" style={{ marginBottom: "1rem" }}>
              <h3 style={{ marginBottom: "0.75rem" }}>Key Performance Indicators</h3>
              <table>
                <thead><tr><th>KPI</th><th>Domain</th><th>Target</th><th>Actual</th><th>Unit</th><th>Health</th></tr></thead>
                <tbody>
                  {perf.kpis.map((k: any, i: number) => (
                    <tr key={i}>
                      <td>{k.name}</td>
                      <td><span className="badge badge-blue">{k.domain}</span></td>
                      <td>{k.target ?? "-"}</td>
                      <td>{k.actual ?? "-"}</td>
                      <td>{k.unit || "-"}</td>
                      <td><span className={`badge badge-${k.health}`}>{k.health}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {perf.deliverable_performance.items.length > 0 && (
            <div className="card" style={{ marginBottom: "1rem" }}>
              <h3 style={{ marginBottom: "0.75rem" }}>Deliverable Performance</h3>
              <table>
                <thead><tr><th>Deliverable</th><th>Status</th><th>Quality</th><th>Completion</th></tr></thead>
                <tbody>
                  {perf.deliverable_performance.items.map((d: any, i: number) => (
                    <tr key={i}>
                      <td>{d.name}</td>
                      <td><span className="badge badge-blue">{d.status.replace(/_/g, " ")}</span></td>
                      <td>{d.quality.replace(/_/g, " ")}</td>
                      <td>
                        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                          <div className="progress-bar" style={{ width: 100 }}>
                            <div className="fill" style={{ width: `${d.completion_pct}%` }} />
                          </div>
                          {d.completion_pct}%
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {perf.stakeholder_engagement.gaps.length > 0 && (
            <div className="card">
              <h3 style={{ marginBottom: "0.75rem" }}>Stakeholder Engagement Gaps</h3>
              <p style={{ fontSize: "0.85rem", color: "var(--gray-500)", marginBottom: "0.75rem" }}>
                Stakeholders where current engagement is below desired level
              </p>
              <table>
                <thead><tr><th>Stakeholder</th><th>Current</th><th>Desired</th><th>Gap</th></tr></thead>
                <tbody>
                  {perf.stakeholder_engagement.gaps.map((g: any, i: number) => (
                    <tr key={i}>
                      <td>{g.name}</td>
                      <td><span className="badge badge-yellow">{g.current}</span></td>
                      <td><span className="badge badge-green">{g.desired}</span></td>
                      <td><span className="badge badge-red">{g.gap} level{g.gap > 1 ? "s" : ""}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
