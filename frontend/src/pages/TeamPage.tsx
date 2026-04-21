import { useState } from "react";
import { useParams } from "react-router-dom";
import {
  useGetTeamMembersQuery,
  useCreateTeamMemberMutation,
  useDeleteTeamMemberMutation,
} from "../services/api";

const ROLES = ["project_manager", "scrum_master", "product_owner", "developer", "analyst", "tester", "designer", "architect", "other"];

export default function TeamPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { data: members = [] } = useGetTeamMembersQuery(projectId!);
  const [create] = useCreateTeamMemberMutation();
  const [remove] = useDeleteTeamMemberMutation();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", role: "developer", responsibilities: "", skills: "", availability: 100 });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await create({ ...form, project_id: projectId });
    setForm({ name: "", email: "", role: "developer", responsibilities: "", skills: "", availability: 100 });
    setShowForm(false);
  };

  return (
    <div>
      <div className="card-header">
        <h2>Team Performance Domain</h2>
        <button className="btn btn-primary" onClick={() => setShowForm(true)}>+ Add Member</button>
      </div>
      <p style={{ color: "var(--gray-500)", marginBottom: "1rem", fontSize: "0.9rem" }}>
        Build high-performing project teams with clear roles and responsibilities (PMBOK 2.2)
      </p>

      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Add Team Member</h3>
            <form onSubmit={handleSubmit}>
              <div className="form-row">
                <div className="form-group">
                  <label>Name</label>
                  <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
                </div>
                <div className="form-group">
                  <label>Email</label>
                  <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Role</label>
                  <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
                    {ROLES.map((r) => <option key={r} value={r}>{r.replace(/_/g, " ")}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label>Availability (%)</label>
                  <input type="number" min={0} max={100} value={form.availability} onChange={(e) => setForm({ ...form, availability: +e.target.value })} />
                </div>
              </div>
              <div className="form-group">
                <label>Skills</label>
                <input value={form.skills} onChange={(e) => setForm({ ...form, skills: e.target.value })} placeholder="Comma-separated skills" />
              </div>
              <div className="form-group">
                <label>Responsibilities</label>
                <textarea value={form.responsibilities} onChange={(e) => setForm({ ...form, responsibilities: e.target.value })} />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn" onClick={() => setShowForm(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Save</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {members.length === 0 ? (
        <div className="empty-state"><p>No team members yet.</p></div>
      ) : (
        <div className="card">
          <table>
            <thead>
              <tr><th>Name</th><th>Email</th><th>Role</th><th>Skills</th><th>Availability</th><th>Actions</th></tr>
            </thead>
            <tbody>
              {members.map((m: any) => (
                <tr key={m.id}>
                  <td>{m.name}</td>
                  <td>{m.email || "-"}</td>
                  <td><span className="badge badge-blue">{m.role?.replace(/_/g, " ")}</span></td>
                  <td>{m.skills || "-"}</td>
                  <td>{m.availability}%</td>
                  <td><button className="btn btn-danger btn-sm" onClick={() => remove(m.id)}>Delete</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
