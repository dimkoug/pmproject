import { useState } from "react";
import { useParams } from "react-router-dom";
import { useGetTimeEntriesQuery, useCreateTimeEntryMutation, useGetTimeSummaryQuery, useGetTasksQuery } from "../services/api";

export default function TimeTrackingPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { data: entries = [], refetch } = useGetTimeEntriesQuery(projectId!);
  const { data: summary } = useGetTimeSummaryQuery(projectId!);
  const { data: tasks = [] } = useGetTasksQuery(projectId!);
  const [create] = useCreateTimeEntryMutation();
  const [form, setForm] = useState({ task_id: "", hours: "", work_date: new Date().toISOString().slice(0, 10), description: "" });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.task_id || !form.hours) return;
    await create({ project_id: projectId, task_id: form.task_id, hours: +form.hours, work_date: form.work_date, description: form.description || null });
    setForm({ ...form, hours: "", description: "" });
    refetch();
  };

  return (
    <div>
      <div style={{ marginBottom: "1.5rem" }}>
        <h2 style={{ fontSize: "1.4rem", fontWeight: 700, marginBottom: "0.3rem" }}>Time Tracking</h2>
        <p style={{ color: "var(--gray-400)", fontSize: "0.85rem" }}>Log hours per task, timesheet summary</p>
      </div>

      <div className="stats-grid">
        <div className="stat-card"><div className="label">Total Hours</div><div className="value">{summary?.total_hours || 0}h</div></div>
        <div className="stat-card"><div className="label">Entries</div><div className="value">{entries.length}</div></div>
      </div>

      <div className="card" style={{ marginBottom: "1.25rem" }}>
        <h3 style={{ marginBottom: "0.75rem" }}>Log Time</h3>
        <form onSubmit={handleSubmit} style={{ display: "flex", gap: "0.5rem", alignItems: "flex-end", flexWrap: "wrap" }}>
          <div className="form-group" style={{ flex: "1 1 180px", marginBottom: 0 }}>
            <label>Task</label>
            <select value={form.task_id} onChange={(e) => setForm({ ...form, task_id: e.target.value })} style={{ width: "100%", padding: "0.45rem 0.65rem", border: "1px solid var(--gray-300)", borderRadius: "var(--radius)", fontSize: "0.835rem", fontFamily: "var(--font-sans)" }}>
              <option value="">Select task...</option>
              {tasks.map((t: any) => <option key={t.id} value={t.id}>{t.title}</option>)}
            </select>
          </div>
          <div className="form-group" style={{ flex: "0 0 80px", marginBottom: 0 }}><label>Hours</label><input type="number" step="0.25" min="0.25" value={form.hours} onChange={(e) => setForm({ ...form, hours: e.target.value })} style={{ width: "100%", padding: "0.45rem 0.5rem", border: "1px solid var(--gray-300)", borderRadius: "var(--radius)", fontSize: "0.835rem" }} /></div>
          <div className="form-group" style={{ flex: "0 0 130px", marginBottom: 0 }}><label>Date</label><input type="date" value={form.work_date} onChange={(e) => setForm({ ...form, work_date: e.target.value })} style={{ width: "100%", padding: "0.45rem 0.5rem", border: "1px solid var(--gray-300)", borderRadius: "var(--radius)", fontSize: "0.835rem" }} /></div>
          <div className="form-group" style={{ flex: "1 1 150px", marginBottom: 0 }}><label>Note</label><input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Optional" style={{ width: "100%", padding: "0.45rem 0.5rem", border: "1px solid var(--gray-300)", borderRadius: "var(--radius)", fontSize: "0.835rem" }} /></div>
          <button type="submit" className="btn btn-primary btn-sm" style={{ padding: "0.47rem 0.85rem", marginBottom: "1px" }}>Log</button>
        </form>
      </div>

      {summary?.by_task?.length > 0 && (
        <div className="card" style={{ marginBottom: "1.25rem" }}>
          <h3 style={{ marginBottom: "0.75rem" }}>Hours by Task</h3>
          {summary.by_task.map((t: any) => (
            <div key={t.task} style={{ display: "flex", alignItems: "center", gap: "0.75rem", padding: "0.4rem 0", borderBottom: "1px solid var(--gray-100)" }}>
              <span style={{ flex: 1, fontSize: "0.85rem" }}>{t.task}</span>
              <div className="progress-bar" style={{ width: 120 }}><div className="fill" style={{ width: `${summary.total_hours > 0 ? (t.hours / summary.total_hours) * 100 : 0}%` }} /></div>
              <span style={{ fontSize: "0.82rem", fontWeight: 600, minWidth: 50, textAlign: "right" }}>{t.hours}h</span>
            </div>
          ))}
        </div>
      )}

      <div className="card">
        <h3 style={{ marginBottom: "0.75rem" }}>Time Log</h3>
        {entries.length === 0 ? <p style={{ color: "var(--gray-400)", fontSize: "0.85rem" }}>No time entries yet.</p> : (
          <table>
            <thead><tr><th>Date</th><th>Task</th><th>User</th><th>Hours</th><th>Note</th></tr></thead>
            <tbody>
              {entries.map((e: any) => (
                <tr key={e.id}><td>{e.work_date}</td><td>{e.task_title}</td><td>{e.user_name}</td><td style={{ fontWeight: 600 }}>{e.hours}h</td><td style={{ color: "var(--gray-500)", fontSize: "0.82rem" }}>{e.description || "-"}</td></tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
