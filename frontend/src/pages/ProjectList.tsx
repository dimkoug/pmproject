import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useGetProjectsQuery, useCreateProjectMutation, useDeleteProjectMutation } from "../services/api";

export default function ProjectList() {
  const { data: projects = [], isLoading } = useGetProjectsQuery();
  const [createProject] = useCreateProjectMutation();
  const [deleteProject] = useDeleteProjectMutation();
  const navigate = useNavigate();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", description: "", development_approach: "predictive" });

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    await createProject(form);
    setForm({ name: "", description: "", development_approach: "predictive" });
    setShowForm(false);
  };

  if (isLoading) return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "60vh" }}>
      <p style={{ color: "var(--gray-400)" }}>Loading projects...</p>
    </div>
  );

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Projects</h1>
          <p className="page-subtitle">PMBOK 7th Edition &middot; 8 Performance Domains</p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <button className="btn" onClick={() => navigate("/portfolio")}>Portfolio</button>
          <button className="btn btn-primary" onClick={() => setShowForm(true)}>+ New Project</button>
        </div>
      </div>

      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Create Project</h3>
            <form onSubmit={handleCreate}>
              <div className="form-group">
                <label>Project Name</label>
                <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Website Redesign" required autoFocus />
              </div>
              <div className="form-group">
                <label>Description</label>
                <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Brief description of the project goals..." />
              </div>
              <div className="form-group">
                <label>Development Approach</label>
                <select value={form.development_approach} onChange={(e) => setForm({ ...form, development_approach: e.target.value })}>
                  <option value="predictive">Predictive</option>
                  <option value="adaptive">Adaptive</option>
                  <option value="hybrid">Hybrid</option>
                  <option value="agile">Agile</option>
                </select>
              </div>
              <div className="modal-actions">
                <button type="button" className="btn" onClick={() => setShowForm(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Create Project</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {projects.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: "4rem 2rem" }}>
          <div style={{ fontSize: "2.5rem", marginBottom: "0.75rem", opacity: 0.15 }}>&#9776;</div>
          <p style={{ color: "var(--gray-500)", fontSize: "0.95rem", marginBottom: "1rem" }}>No projects yet</p>
          <button className="btn btn-primary" onClick={() => setShowForm(true)}>Create your first project</button>
        </div>
      ) : (
        <div className="project-grid">
          {projects.map((p: any) => (
            <div key={p.id} className="project-card" onClick={() => navigate(`/projects/${p.id}`)}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.5rem" }}>
                <h3>{p.name}</h3>
                <span className="badge badge-blue">{p.status}</span>
              </div>
              <p style={{ fontSize: "0.835rem", color: "var(--gray-500)", marginBottom: "1rem", lineHeight: 1.5 }}>
                {p.description?.slice(0, 120) || "No description provided"}
              </p>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span className="badge badge-gray">{p.development_approach}</span>
                <button
                  className="btn btn-danger btn-sm"
                  onClick={(e) => { e.stopPropagation(); deleteProject(p.id); }}
                >
                  Remove
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
