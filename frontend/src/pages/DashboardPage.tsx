import { useParams } from "react-router-dom";
import { useGetDashboardQuery, useGetProjectQuery } from "../services/api";
import { useAppSelector } from "../app/hooks";

export default function DashboardPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { data: project } = useGetProjectQuery(projectId!);
  const { data: dashboard, isLoading } = useGetDashboardQuery(projectId!);
  const events = useAppSelector((s) => s.ws.events);

  if (isLoading) return <p style={{ color: "var(--gray-400)", padding: "2rem 0" }}>Loading dashboard...</p>;

  const taskTotal = Object.values(dashboard?.task_stats || {}).reduce((a: number, b: any) => a + b, 0) as number;
  const tasksDone = (dashboard?.task_stats?.done || 0) as number;

  return (
    <div>
      <div style={{ marginBottom: "1.75rem" }}>
        <h2 style={{ fontSize: "1.4rem", fontWeight: 700, letterSpacing: "-0.02em", marginBottom: "0.3rem" }}>Dashboard</h2>
        <p style={{ color: "var(--gray-400)", fontSize: "0.85rem" }}>
          {project?.development_approach} approach &middot; {project?.status}
        </p>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="label">Total Tasks</div>
          <div className="value">{taskTotal}</div>
        </div>
        <div className="stat-card">
          <div className="label">Tasks Done</div>
          <div className="value">{tasksDone}</div>
        </div>
        <div className="stat-card">
          <div className="label">Open Risks</div>
          <div className="value">
            {(dashboard?.risk_stats?.identified || 0) + (dashboard?.risk_stats?.analyzing || 0) + (dashboard?.risk_stats?.active || 0)}
          </div>
        </div>
        <div className="stat-card">
          <div className="label">Stakeholders</div>
          <div className="value">{dashboard?.stakeholder_count || 0}</div>
        </div>
        <div className="stat-card">
          <div className="label">Team Members</div>
          <div className="value">{dashboard?.team_count || 0}</div>
        </div>
        <div className="stat-card">
          <div className="label">Change Requests</div>
          <div className="value">{dashboard?.change_request_count || 0}</div>
        </div>
      </div>

      {taskTotal > 0 && (
        <div className="card">
          <h3 style={{ marginBottom: "0.75rem" }}>Task Progress</h3>
          <div className="progress-bar">
            <div className="fill" style={{ width: `${taskTotal > 0 ? (tasksDone / taskTotal) * 100 : 0}%` }} />
          </div>
          <p style={{ fontSize: "0.85rem", color: "var(--gray-500)", marginTop: "0.5rem" }}>
            {tasksDone} of {taskTotal} tasks completed ({taskTotal > 0 ? Math.round((tasksDone / taskTotal) * 100) : 0}%)
          </p>
        </div>
      )}

      <div className="card">
        <div className="card-header">
          <h3>Task Distribution</h3>
        </div>
        <table>
          <thead>
            <tr><th>Status</th><th>Count</th></tr>
          </thead>
          <tbody>
            {Object.entries(dashboard?.task_stats || {}).map(([status, count]: any) => (
              <tr key={status}><td>{status}</td><td>{count}</td></tr>
            ))}
          </tbody>
        </table>
      </div>

      {dashboard?.measurements?.length > 0 && (
        <div className="card">
          <h3 style={{ marginBottom: "0.75rem" }}>Key Measurements</h3>
          <table>
            <thead>
              <tr><th>Name</th><th>Domain</th><th>Target</th><th>Actual</th><th>Unit</th></tr>
            </thead>
            <tbody>
              {dashboard.measurements.map((m: any) => (
                <tr key={m.id}>
                  <td>{m.name}</td>
                  <td><span className="badge badge-blue">{m.domain}</span></td>
                  <td>{m.target_value ?? "-"}</td>
                  <td>{m.actual_value ?? "-"}</td>
                  <td>{m.unit || "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="card">
        <div className="card-header">
          <h3>Live Activity</h3>
        </div>
        {events.length === 0 ? (
          <p style={{ color: "var(--gray-500)", fontSize: "0.85rem" }}>No activity yet. Changes will appear here in real-time.</p>
        ) : (
          <div className="activity-feed">
            {[...events].reverse().map((ev, i) => (
              <div key={i} className="activity-item">
                <span className="time">{new Date(ev.timestamp).toLocaleTimeString()}</span>
                <span>{ev.event.replace(/_/g, " ")}: {ev.data.name || ev.data.title || ev.data.id}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
