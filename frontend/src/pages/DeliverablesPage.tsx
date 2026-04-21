import { useState } from "react";
import { useParams } from "react-router-dom";
import {
  useGetDeliverablesQuery,
  useCreateDeliverableMutation,
  useUpdateDeliverableMutation,
  useDeleteDeliverableMutation,
} from "../services/api";

const DEL_STATUSES = ["planned", "in_progress", "ready_for_review", "accepted", "rejected"];
const QUALITY_LEVELS = ["not_assessed", "below_standard", "meets_standard", "exceeds_standard"];

const statusColor = (s: string) => {
  if (s === "accepted") return "badge-green";
  if (s === "rejected") return "badge-red";
  if (s === "in_progress") return "badge-blue";
  return "badge-gray";
};

export default function DeliverablesPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { data: deliverables = [] } = useGetDeliverablesQuery(projectId!);
  const [create] = useCreateDeliverableMutation();
  const [update] = useUpdateDeliverableMutation();
  const [remove] = useDeleteDeliverableMutation();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    name: "", description: "", acceptance_criteria: "", completion_percentage: 0,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await create({ ...form, project_id: projectId });
    setForm({ name: "", description: "", acceptance_criteria: "", completion_percentage: 0 });
    setShowForm(false);
  };

  return (
    <div>
      <div className="card-header">
        <h2>Delivery Performance Domain</h2>
        <button className="btn btn-primary" onClick={() => setShowForm(true)}>+ Add Deliverable</button>
      </div>
      <p style={{ color: "var(--gray-500)", marginBottom: "1rem", fontSize: "0.9rem" }}>
        Track deliverables, quality, and value delivery outcomes (PMBOK 2.6)
      </p>

      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Add Deliverable</h3>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Name</label>
                <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
              </div>
              <div className="form-group">
                <label>Description</label>
                <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
              </div>
              <div className="form-group">
                <label>Acceptance Criteria</label>
                <textarea value={form.acceptance_criteria} onChange={(e) => setForm({ ...form, acceptance_criteria: e.target.value })} />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn" onClick={() => setShowForm(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Save</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {deliverables.length === 0 ? (
        <div className="empty-state"><p>No deliverables yet.</p></div>
      ) : (
        <div className="card">
          <table>
            <thead>
              <tr><th>Name</th><th>Status</th><th>Quality</th><th>Completion</th><th>Actions</th></tr>
            </thead>
            <tbody>
              {deliverables.map((d: any) => (
                <tr key={d.id}>
                  <td>
                    <div>{d.name}</div>
                    {d.acceptance_criteria && (
                      <div style={{ fontSize: "0.78rem", color: "var(--gray-500)" }}>Criteria: {d.acceptance_criteria.slice(0, 60)}</div>
                    )}
                  </td>
                  <td>
                    <select
                      value={d.status}
                      onChange={(e) => update({ id: d.id, body: { status: e.target.value } })}
                      style={{ fontSize: "0.8rem", padding: "0.2rem" }}
                    >
                      {DEL_STATUSES.map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
                    </select>
                  </td>
                  <td>
                    <select
                      value={d.quality_level}
                      onChange={(e) => update({ id: d.id, body: { quality_level: e.target.value } })}
                      style={{ fontSize: "0.8rem", padding: "0.2rem" }}
                    >
                      {QUALITY_LEVELS.map((q) => <option key={q} value={q}>{q.replace(/_/g, " ")}</option>)}
                    </select>
                  </td>
                  <td>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                      <div className="progress-bar" style={{ width: 100 }}>
                        <div className="fill" style={{ width: `${d.completion_percentage}%` }} />
                      </div>
                      <input
                        type="number" min={0} max={100}
                        value={d.completion_percentage}
                        onChange={(e) => update({ id: d.id, body: { completion_percentage: +e.target.value } })}
                        style={{ width: 50, fontSize: "0.8rem", padding: "0.15rem" }}
                      />%
                    </div>
                  </td>
                  <td><button className="btn btn-danger btn-sm" onClick={() => remove(d.id)}>Delete</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
