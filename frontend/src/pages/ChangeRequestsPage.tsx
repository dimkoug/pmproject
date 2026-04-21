import { useState } from "react";
import { useParams } from "react-router-dom";
import {
  useGetChangeRequestsQuery,
  useCreateChangeRequestMutation,
  useUpdateChangeRequestMutation,
  useDeleteChangeRequestMutation,
} from "../services/api";

const CR_STATUSES = ["submitted", "under_review", "approved", "rejected", "implemented", "deferred"];
const IMPACTS = ["low", "medium", "high", "critical"];

const statusColor = (s: string) => {
  if (s === "approved" || s === "implemented") return "badge-green";
  if (s === "rejected") return "badge-red";
  if (s === "under_review") return "badge-yellow";
  return "badge-gray";
};

const impactColor = (i: string) => {
  if (i === "critical") return "badge-red";
  if (i === "high") return "badge-yellow";
  return "badge-gray";
};

export default function ChangeRequestsPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { data: crs = [] } = useGetChangeRequestsQuery(projectId!);
  const [create] = useCreateChangeRequestMutation();
  const [update] = useUpdateChangeRequestMutation();
  const [remove] = useDeleteChangeRequestMutation();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    title: "", description: "", justification: "", impact: "medium", impact_analysis: "",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await create({ ...form, project_id: projectId });
    setForm({ title: "", description: "", justification: "", impact: "medium", impact_analysis: "" });
    setShowForm(false);
  };

  return (
    <div>
      <div className="card-header">
        <h2>Change Management</h2>
        <button className="btn btn-primary" onClick={() => setShowForm(true)}>+ New Change Request</button>
      </div>
      <p style={{ color: "var(--gray-500)", marginBottom: "1rem", fontSize: "0.9rem" }}>
        Enable change to achieve the envisioned future state (PMBOK Principle 3.12)
      </p>

      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Submit Change Request</h3>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Title</label>
                <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
              </div>
              <div className="form-group">
                <label>Description</label>
                <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
              </div>
              <div className="form-group">
                <label>Justification</label>
                <textarea value={form.justification} onChange={(e) => setForm({ ...form, justification: e.target.value })} />
              </div>
              <div className="form-group">
                <label>Impact Level</label>
                <select value={form.impact} onChange={(e) => setForm({ ...form, impact: e.target.value })}>
                  {IMPACTS.map((i) => <option key={i} value={i}>{i}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Impact Analysis</label>
                <textarea value={form.impact_analysis} onChange={(e) => setForm({ ...form, impact_analysis: e.target.value })} />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn" onClick={() => setShowForm(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Submit</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {crs.length === 0 ? (
        <div className="empty-state"><p>No change requests yet.</p></div>
      ) : (
        <div className="card">
          <table>
            <thead>
              <tr><th>Title</th><th>Impact</th><th>Status</th><th>Justification</th><th>Actions</th></tr>
            </thead>
            <tbody>
              {crs.map((cr: any) => (
                <tr key={cr.id}>
                  <td>
                    <div>{cr.title}</div>
                    {cr.description && <div style={{ fontSize: "0.78rem", color: "var(--gray-500)" }}>{cr.description.slice(0, 80)}</div>}
                  </td>
                  <td><span className={`badge ${impactColor(cr.impact)}`}>{cr.impact}</span></td>
                  <td>
                    <select
                      value={cr.status}
                      onChange={(e) => update({ id: cr.id, body: { status: e.target.value } })}
                      style={{ fontSize: "0.8rem", padding: "0.2rem" }}
                    >
                      {CR_STATUSES.map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
                    </select>
                  </td>
                  <td>{cr.justification?.slice(0, 60) || "-"}</td>
                  <td><button className="btn btn-danger btn-sm" onClick={() => remove(cr.id)}>Delete</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
