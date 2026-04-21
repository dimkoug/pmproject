import { useState } from "react";
import { useParams } from "react-router-dom";
import { useGetSprintsQuery, useCreateSprintMutation, useUpdateSprintStatusMutation, useGetSprintVelocityQuery } from "../services/api";
import VelocityChart from "../components/charts/VelocityChart";

export default function SprintPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { data: sprints = [], refetch } = useGetSprintsQuery(projectId!);
  const { data: velocity = [] } = useGetSprintVelocityQuery(projectId!);
  const [create] = useCreateSprintMutation();
  const [updateStatus] = useUpdateSprintStatusMutation();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", goal: "", sprint_number: 1, start_date: "", end_date: "" });

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    await create({ ...form, project_id: projectId, sprint_number: +form.sprint_number, start_date: form.start_date || null, end_date: form.end_date || null });
    setShowForm(false);
    refetch();
  };

  const avgVelocity = velocity.length > 0 ? Math.round(velocity.reduce((s: number, v: any) => s + v.points, 0) / velocity.length) : 0;

  return (
    <div>
      <div className="card-header">
        <h2>Sprint Planning</h2>
        <button className="btn btn-primary" onClick={() => setShowForm(true)}>+ New Sprint</button>
      </div>
      <p style={{ color: "var(--gray-400)", fontSize: "0.85rem", marginBottom: "1rem" }}>Agile sprint management and velocity tracking</p>

      <div className="stats-grid">
        <div className="stat-card"><div className="label">Sprints</div><div className="value">{sprints.length}</div></div>
        <div className="stat-card"><div className="label">Avg Velocity</div><div className="value">{avgVelocity} pts</div></div>
      </div>

      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Create Sprint</h3>
            <form onSubmit={handleCreate}>
              <div className="form-row">
                <div className="form-group"><label>Sprint Name</label><input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required autoFocus placeholder="Sprint 1" /></div>
                <div className="form-group"><label>Number</label><input type="number" value={form.sprint_number} onChange={(e) => setForm({ ...form, sprint_number: +e.target.value })} /></div>
              </div>
              <div className="form-group"><label>Goal</label><input value={form.goal} onChange={(e) => setForm({ ...form, goal: e.target.value })} placeholder="What should this sprint achieve?" /></div>
              <div className="form-row">
                <div className="form-group"><label>Start Date</label><input type="date" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} /></div>
                <div className="form-group"><label>End Date</label><input type="date" value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })} /></div>
              </div>
              <div className="modal-actions">
                <button type="button" className="btn" onClick={() => setShowForm(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Create</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {sprints.length === 0 ? <div className="empty-state"><p>No sprints created yet.</p></div> : (
        <div className="card">
          <table>
            <thead><tr><th>Sprint</th><th>Goal</th><th>Status</th><th>Dates</th><th>Tasks</th><th>Points</th><th>Actions</th></tr></thead>
            <tbody>
              {sprints.map((s: any) => (
                <tr key={s.id}>
                  <td style={{ fontWeight: 600 }}>{s.name}</td>
                  <td style={{ fontSize: "0.82rem", color: "var(--gray-500)" }}>{s.goal || "-"}</td>
                  <td><span className={`badge ${s.status === "active" ? "badge-blue" : s.status === "completed" ? "badge-green" : "badge-gray"}`}>{s.status}</span></td>
                  <td style={{ fontSize: "0.82rem" }}>{s.start_date || "?"} - {s.end_date || "?"}</td>
                  <td>{s.done_tasks}/{s.total_tasks}</td>
                  <td>{s.done_points}/{s.total_points}</td>
                  <td>
                    {s.status === "planning" && <button className="btn btn-primary btn-sm" onClick={() => { updateStatus({ sprintId: s.id, status: "active" }); refetch(); }}>Start</button>}
                    {s.status === "active" && <button className="btn btn-sm" onClick={() => { updateStatus({ sprintId: s.id, status: "completed" }); refetch(); }}>Complete</button>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {velocity.length > 0 && (
        <div className="card" style={{ marginTop: "1.25rem" }}>
          <h3 style={{ marginBottom: "0.75rem" }}>Velocity Chart</h3>
          <VelocityChart sprints={velocity.map((v: any) => ({ sprint: v.sprint, points: v.points }))} average={avgVelocity} />
        </div>
      )}
    </div>
  );
}
