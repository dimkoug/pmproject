import { useState } from "react";
import { useParams } from "react-router-dom";
import {
  useGetStakeholdersQuery,
  useCreateStakeholderMutation,
  useUpdateStakeholderMutation,
  useDeleteStakeholderMutation,
} from "../services/api";

const ENGAGEMENT_LEVELS = ["unaware", "resistant", "neutral", "supportive", "leading"];
const CATEGORIES = ["sponsor", "customer", "end_user", "regulator", "supplier", "internal", "external"];

const engagementColor = (level: string) => {
  if (level === "leading" || level === "supportive") return "badge-green";
  if (level === "neutral") return "badge-yellow";
  return "badge-red";
};

export default function StakeholdersPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { data: stakeholders = [] } = useGetStakeholdersQuery(projectId!);
  const [create] = useCreateStakeholderMutation();
  const [update] = useUpdateStakeholderMutation();
  const [remove] = useDeleteStakeholderMutation();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    name: "", role: "", email: "", category: "internal",
    engagement_level: "neutral", desired_engagement: "supportive",
    influence: "medium", interest: "medium", expectations: "", communication_needs: "",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await create({ ...form, project_id: projectId });
    setForm({ name: "", role: "", email: "", category: "internal", engagement_level: "neutral", desired_engagement: "supportive", influence: "medium", interest: "medium", expectations: "", communication_needs: "" });
    setShowForm(false);
  };

  return (
    <div>
      <div className="card-header">
        <h2>Stakeholder Performance Domain</h2>
        <button className="btn btn-primary" onClick={() => setShowForm(true)}>+ Add Stakeholder</button>
      </div>
      <p style={{ color: "var(--gray-500)", marginBottom: "1rem", fontSize: "0.9rem" }}>
        Manage stakeholder engagement levels, influence, and communication needs (PMBOK 2.1)
      </p>

      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Add Stakeholder</h3>
            <form onSubmit={handleSubmit}>
              <div className="form-row">
                <div className="form-group">
                  <label>Name</label>
                  <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
                </div>
                <div className="form-group">
                  <label>Role</label>
                  <input value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Email</label>
                  <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
                </div>
                <div className="form-group">
                  <label>Category</label>
                  <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
                    {CATEGORIES.map((c) => <option key={c} value={c}>{c.replace(/_/g, " ")}</option>)}
                  </select>
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Current Engagement</label>
                  <select value={form.engagement_level} onChange={(e) => setForm({ ...form, engagement_level: e.target.value })}>
                    {ENGAGEMENT_LEVELS.map((l) => <option key={l} value={l}>{l}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label>Desired Engagement</label>
                  <select value={form.desired_engagement} onChange={(e) => setForm({ ...form, desired_engagement: e.target.value })}>
                    {ENGAGEMENT_LEVELS.map((l) => <option key={l} value={l}>{l}</option>)}
                  </select>
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Influence</label>
                  <select value={form.influence} onChange={(e) => setForm({ ...form, influence: e.target.value })}>
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Interest</label>
                  <select value={form.interest} onChange={(e) => setForm({ ...form, interest: e.target.value })}>
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select>
                </div>
              </div>
              <div className="form-group">
                <label>Expectations</label>
                <textarea value={form.expectations} onChange={(e) => setForm({ ...form, expectations: e.target.value })} />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn" onClick={() => setShowForm(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Save</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {stakeholders.length === 0 ? (
        <div className="empty-state"><p>No stakeholders yet.</p></div>
      ) : (
        <div className="card">
          <table>
            <thead>
              <tr>
                <th>Name</th><th>Role</th><th>Category</th><th>Current</th><th>Desired</th><th>Influence</th><th>Interest</th><th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {stakeholders.map((s: any) => (
                <tr key={s.id}>
                  <td>{s.name}</td>
                  <td>{s.role || "-"}</td>
                  <td><span className="badge badge-gray">{s.category?.replace(/_/g, " ")}</span></td>
                  <td><span className={`badge ${engagementColor(s.engagement_level)}`}>{s.engagement_level}</span></td>
                  <td><span className={`badge ${engagementColor(s.desired_engagement)}`}>{s.desired_engagement}</span></td>
                  <td>{s.influence}</td>
                  <td>{s.interest}</td>
                  <td>
                    <button className="btn btn-danger btn-sm" onClick={() => remove(s.id)}>Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
